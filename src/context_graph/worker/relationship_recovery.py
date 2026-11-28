"""Bounded relationship-only recovery; original source is revalidated on every retry."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from context_graph.domain.models import Event
from context_graph.ports.errors import RuntimeFencedError
from context_graph.ports.event_log import AcceptedRecordReader
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite
from context_graph.ports.relationship_recovery import CURSOR_LABEL

if TYPE_CHECKING:
    from context_graph.domain.pack_projection import PackProjector, ProjectionPlan
    from context_graph.ports.event_log import EventLog
    from context_graph.ports.pack_graph import PackGraph

TERMINAL = {"recovered", "existing_relationship_kept"}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def edge_identity(edge: EdgeWrite) -> list[Any]:
    return [edge.edge_type, asdict(edge.source), asdict(edge.target)]


def effect_digest(edge: EdgeWrite, selector: str | None = None) -> str:
    return digest([asdict(edge), selector])


@dataclass
class RecoveryReport:
    scanned: int = 0
    waiting: int = 0
    blocking: int = 0
    complete_scan: bool = True

    @property
    def complete(self) -> bool:
        return self.complete_scan and self.blocking == 0


class RelationshipRecovery:
    """One coordinator per consumer; state is in the tenant's graph, not this object."""

    def __init__(
        self, graph: PackGraph, log: EventLog, projector: PackProjector, *, timeout_s: float = 5.0
    ) -> None:
        self.graph, self.log, self.projector = graph, log, projector
        self.timeout_s = timeout_s

    async def capture(
        self,
        plans: list[ProjectionPlan],
        resolved: dict[int, list[EdgeWrite]],
        truncated: set[int] | None = None,
    ) -> set[int]:
        candidates: list[tuple[ProjectionPlan, EdgeWrite, str | None]] = [
            (plan, edge, None)
            for plan in plans
            for edge in plan.edges
            if edge.edge_type != "DERIVED_FROM"
        ]
        candidates += [
            (plan, edge, digest(asdict(lookup)))
            for plan in plans
            for lookup in plan.lookups
            for edge in resolved.get(id(lookup), [])
        ]
        for plan in plans:
            for lookup in plan.lookups:
                if id(lookup) not in (truncated or set()):
                    continue
                descriptor = digest(asdict(lookup))
                effect = digest(["truncated_lookup", descriptor])
                key = digest([plan.event_id, plan.bundle, effect])
                await self.graph.put_relationship_intent(
                    {
                        "node_id": key,
                        "kind": "blocked_lookup",
                        "generation": digest([plan.event_id, plan.bundle, effect]),
                        "event_id": plan.event_id,
                        "bundle": plan.bundle,
                        "authority": plan.authority,
                        "effect_digest": effect,
                        "position": plan.event_position,
                        "order_key": self.log.position_order_key(plan.event_position),
                        "required": True,
                        "status": "ambiguous_or_truncated_lookup",
                    }
                )
        refs = list(
            {ref for _plan, edge, _selector in candidates for ref in (edge.source, edge.target)}
        )
        existing = await self.graph.get_nodes(refs) if refs else {}
        previous = await self.graph.get_relationship_intents(
            list({digest(edge_identity(edge)) for _plan, edge, _selector in candidates})
        )
        suppressed: set[int] = set()
        for plan, edge, selector in candidates:
            key = digest(edge_identity(edge))
            prior = previous.get(key)
            missing = edge.source not in existing or edge.target not in existing
            if not missing and prior is None:
                continue
            if not plan.event_id or not plan.event_position:
                raise ValueError(
                    "Relationship recovery requires a pinned source event and log position"
                )
            order = self.log.position_order_key(plan.event_position)
            if prior is not None and order <= prior["order_key"]:
                suppressed.add(id(edge))
                continue
            if missing:
                suppressed.add(id(edge))
            effect = effect_digest(edge, selector)
            await self.graph.put_relationship_intent(
                {
                    "node_id": key,
                    "generation": digest([plan.event_id, plan.bundle, effect]),
                    "event_id": plan.event_id,
                    "bundle": plan.bundle,
                    "authority": plan.authority,
                    "effect_digest": effect,
                    "selector_digest": selector,
                    "position": plan.event_position,
                    "order_key": order,
                    "edge_type": edge.edge_type,
                    "source": asdict(edge.source),
                    "target": asdict(edge.target),
                    "required": edge.required,
                    "status": "endpoint_missing",
                }
            )
        return suppressed

    async def _recover(self, row: dict[str, Any]) -> str:
        if row["status"] in TERMINAL or row.get("kind") == "blocked_lookup":
            return str(row["status"])
        if row["node_id"] != digest([row["edge_type"], row["source"], row["target"]]) or row[
            "generation"
        ] != digest([row["event_id"], row["bundle"], row["effect_digest"]]):
            return await self.graph.settle_relationship_intent(
                row["node_id"], row["generation"], "invalid_intent"
            )
        status = "changed_authority"
        if row["authority"] == self.projector.authority_fingerprint:
            provenance = None
            document: dict[str, Any] | None
            if self.projector.requires_provenance:
                if not isinstance(self.log, AcceptedRecordReader):
                    raise ValueError("Recovery requires an accepted-record reader")
                records = await self.log.get_accepted_records([row["event_id"]])
                document, provenance = records[0].document, records[0].provenance
            else:
                document = (await self.log.get_documents([row["event_id"]]))[0]
            if document is None:
                status = "missing_source"
            else:
                event = Event.model_validate(document, strict=False)
                if str(event.event_id) != row["event_id"]:
                    status = "changed_source"
                else:
                    event = event.model_copy(update={"global_position": row["position"]})
                    plan = self.projector.plan(event, document, provenance=provenance)
                    edges: list[tuple[EdgeWrite, str | None]] = [
                        (edge, None) for edge in plan.edges
                    ]
                    # Re-derive lookup properties, but NEVER choose a different target.
                    from context_graph.worker.pack_projection import _edges

                    for lookup in plan.lookups:
                        if lookup.edge_type != row["edge_type"] or digest(
                            asdict(lookup)
                        ) != row.get("selector_digest"):
                            continue
                        known = row["target"] if lookup.reverse else row["source"]
                        found = row["source"] if lookup.reverse else row["target"]
                        if asdict(lookup.known) == known and lookup.label == found["label"]:
                            edges.extend(
                                (edge, digest(asdict(lookup)))
                                for edge in _edges(lookup, [{lookup.key_property: found["key"]}])
                            )
                    matching = [
                        e
                        for e, selector in edges
                        if edge_identity(e) == [row["edge_type"], row["source"], row["target"]]
                        and effect_digest(e, selector) == row["effect_digest"]
                    ]
                    if matching:
                        edge = matching[-1]
                        # A create path cannot remove a property; removals are vacuous.
                        insert = EdgeWrite(
                            edge.edge_type,
                            edge.source,
                            edge.target,
                            edge.properties,
                            create_only=True,
                        )
                        return await self.graph.settle_relationship_intent(
                            row["node_id"], row["generation"], "waiting", insert
                        )
                    status = "changed_bundle" if row["bundle"] != plan.bundle else "changed_source"
        return await self.graph.settle_relationship_intent(
            row["node_id"], row["generation"], status
        )

    async def page(self, limit: int = 100) -> RecoveryReport:
        async with asyncio.timeout(self.timeout_s):
            return await self._page(limit)

    async def _page(self, limit: int) -> RecoveryReport:
        cursor = NodeRef(CURSOR_LABEL, "relationships")
        found = await self.graph.get_nodes([cursor])
        if not isinstance(found, dict):
            raise RuntimeFencedError("Backend returned an invalid recovery cursor")
        saved = found.get(cursor, {})
        after = saved.get("after") or None
        rows = await self.graph.relationship_intents(after, limit)
        if not isinstance(rows, list):
            raise RuntimeFencedError("Backend returned an invalid recovery page")
        if not rows and after:
            rows = await self.graph.relationship_intents(None, limit)
        if rows:
            # Persist progress before processing so a crashing first page cannot starve later rows.
            await self.graph.upsert_nodes([NodeWrite(cursor, {"after": rows[-1]["node_id"]})])
        report = await self._rows(rows)
        report.complete_scan = not bool(rows)
        return report

    async def _rows(self, rows: list[dict[str, Any]]) -> RecoveryReport:
        report = RecoveryReport()
        for row in rows:
            status = await self._recover(row)
            report.scanned += 1
            if status not in TERMINAL and status != "superseded":
                report.waiting += 1
                report.blocking += int(row["required"] or status != "endpoint_missing")
        return report

    async def finish(self, budget: int = 10_000, page_size: int = 100) -> RecoveryReport:
        async with asyncio.timeout(self.timeout_s):
            return await self._finish(budget, page_size)

    async def _finish(self, budget: int, page_size: int) -> RecoveryReport:
        report, after = RecoveryReport(), None
        while report.scanned < budget:
            rows = await self.graph.relationship_intents(
                after, min(page_size, budget - report.scanned)
            )
            if not isinstance(rows, list):
                raise RuntimeFencedError("Backend returned an invalid recovery page")
            if not rows:
                return report
            part = await self._rows(rows)
            report.scanned += part.scanned
            report.waiting += part.waiting
            report.blocking += part.blocking
            after = rows[-1]["node_id"]
        report.complete_scan = not bool(await self.graph.relationship_intents(after, 1))
        return report
