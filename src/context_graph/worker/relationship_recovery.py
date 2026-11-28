"""Bounded relationship-only recovery; original source is revalidated on every retry."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from context_graph.domain.models import Event
from context_graph.domain.relationship_recovery import intent_generation, semantic_digest
from context_graph.domain.relationship_recovery import recovery_digest as digest
from context_graph.ports.errors import RuntimeFencedError
from context_graph.ports.event_log import AcceptedRecordReader
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite
from context_graph.ports.relationship_recovery import CURSOR_LABEL

if TYPE_CHECKING:
    from context_graph.domain.pack_projection import PackProjector, ProjectionPlan
    from context_graph.domain.source_trust import VerifiedSourceProvenance
    from context_graph.ports.event_log import EventLog
    from context_graph.ports.pack_graph import PackGraph

TERMINAL = {"recovered", "existing_relationship_kept", "superseded_by_replay"}


def edge_identity(edge: EdgeWrite) -> list[Any]:
    return [edge.edge_type, asdict(edge.source), asdict(edge.target)]


def effect_descriptor(write: Any) -> dict[str, Any]:
    # Only optional descriptor fields / ignored top-level assignments are
    # absent-equivalent. Nested business JSON nulls are meaningful values.
    data = {name: value for name, value in asdict(write).items() if value is not None}
    if "properties" in data:
        data["properties"] = {
            name: value for name, value in data["properties"].items() if value is not None
        }
    return data


def effect_digest(edge: EdgeWrite, selector: str | None = None) -> str:
    return semantic_digest([effect_descriptor(edge), selector])


def relationship_plan_digest(plan: ProjectionPlan) -> str:
    return semantic_digest(
        [
            [effect_descriptor(edge) for edge in plan.edges],
            [effect_descriptor(lookup) for lookup in plan.lookups],
        ]
    )


@dataclass
class RecoveryReport:
    scanned: int = 0
    waiting: int = 0
    blocking: int = 0
    complete_scan: bool = True

    @property
    def complete(self) -> bool:
        return self.complete_scan and self.blocking == 0


@dataclass
class CaptureReport:
    suppressed: set[int]
    written: int = 0


class RelationshipRecovery:
    """One coordinator per consumer; state is in the tenant's graph, not this object."""

    def __init__(
        self,
        graph: PackGraph,
        log: EventLog,
        projector: PackProjector,
        *,
        timeout_s: float = 5.0,
        reinterpreting: bool = False,
    ) -> None:
        self.graph, self.log, self.projector = graph, log, projector
        self.timeout_s = timeout_s
        self.reinterpreting = reinterpreting

    async def capture(
        self,
        plans: list[ProjectionPlan],
        resolved: dict[int, list[EdgeWrite]],
        truncated: set[int] | None = None,
    ) -> CaptureReport:
        candidates: list[tuple[ProjectionPlan, EdgeWrite, str | None]] = [
            (plan, edge, None) for plan in plans for edge in plan.edges
        ]
        candidates += [
            (plan, edge, semantic_digest(effect_descriptor(lookup)))
            for plan in plans
            for lookup in plan.lookups
            for edge in resolved.get(id(lookup), [])
        ]
        for plan in plans:
            for lookup in plan.lookups:
                if id(lookup) not in (truncated or set()):
                    continue
                descriptor = semantic_digest(effect_descriptor(lookup))
                effect = digest(["truncated_lookup", descriptor])
                key = digest([plan.event_id, "blocked_lookup"])
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
                        "source_digest": plan.source_digest,
                    },
                    reinterpret=self.reinterpreting,
                )
        if self.reinterpreting:
            # Only an explicitly replayed, source-verified event can retire its
            # own old diagnostic; unrelated/rejected events remain blocking.
            for plan in plans:
                if any(id(lookup) in (truncated or set()) for lookup in plan.lookups):
                    continue
                key = digest([plan.event_id, "blocked_lookup"])
                previous_block = (await self.graph.get_relationship_intents([key])).get(key)
                if previous_block is not None:
                    if previous_block.get("source_digest") != plan.source_digest:
                        raise RuntimeFencedError("Blocked lookup source changed")
                    await self.graph.settle_relationship_intent(
                        key, previous_block["generation"], "superseded_by_replay"
                    )
        refs = list(
            {ref for _plan, edge, _selector in candidates for ref in (edge.source, edge.target)}
        )
        existing = await self.graph.get_nodes(refs) if refs else {}
        previous = await self.graph.get_relationship_intents(
            list({digest(edge_identity(edge)) for _plan, edge, _selector in candidates})
        )
        suppressed: set[int] = set()
        written = 0
        ordinals: dict[int, int] = {}
        for plan, edge, selector in candidates:
            ordinal = ordinals.get(id(plan), 0)
            ordinals[id(plan)] = ordinal + 1
            key = digest(edge_identity(edge))
            prior = previous.get(key)
            replacing = bool(self.reinterpreting and prior and prior["bundle"] != plan.bundle)
            missing = edge.source not in existing or edge.target not in existing
            if not missing and prior is None and not replacing:
                continue
            if not plan.event_id or not plan.event_position or not plan.source_digest:
                raise ValueError(
                    "Relationship recovery requires a pinned source event and log position"
                )
            order = f"{self.log.position_order_key(plan.event_position)}/{ordinal:010d}"
            suppressed.add(id(edge))
            effect = effect_digest(edge, selector)
            await self.graph.put_relationship_intent(
                {
                    "node_id": key,
                    "generation": digest([plan.event_id, plan.bundle, effect]),
                    "event_id": plan.event_id,
                    "bundle": plan.bundle,
                    "authority": plan.authority,
                    "source_id": plan.source_id,
                    "source_digest": plan.source_digest,
                    "effect_digest": effect,
                    "selector_digest": selector,
                    "plan_digest": relationship_plan_digest(plan),
                    "writes": sorted(
                        {name for name, value in edge.properties.items() if value is not None}
                        | set(edge.remove_properties)
                    ),
                    "position": plan.event_position,
                    "order_key": order,
                    "edge_type": edge.edge_type,
                    "source": asdict(edge.source),
                    "target": asdict(edge.target),
                    "required": edge.required,
                    "status": "endpoint_missing",
                    "apply_existing": not missing,
                    "normal_patch": bool(
                        self.reinterpreting or (prior and order > prior["order_key"])
                    ),
                },
                reinterpret=self.reinterpreting,
            )
            current = (await self.graph.get_relationship_intents([key]))[key]
            previous[key] = current
            if prior is not None and not missing and current["status"] not in TERMINAL:
                # The tracked effect and terminal status commit in one native unit.
                status = await self._recover(current)
                written += int(status in TERMINAL)
        return CaptureReport(suppressed, written)

    async def _recover(self, row: dict[str, Any]) -> str:
        if row["status"] in TERMINAL or row.get("kind") == "blocked_lookup":
            return str(row["status"])
        if row["node_id"] != digest([row["edge_type"], row["source"], row["target"]]) or row[
            "generation"
        ] != intent_generation(row):
            return await self.graph.settle_relationship_intent(
                row["node_id"], row["generation"], "invalid_intent"
            )
        properties: dict[str, Any] = {}
        removals: set[str] = set()
        ids = sorted({pointer["event_id"] for pointer in row["effects"]})
        sources: dict[str, tuple[dict[str, Any] | None, VerifiedSourceProvenance | None]]
        if self.projector.requires_provenance:
            if not isinstance(self.log, AcceptedRecordReader):
                raise RuntimeFencedError("Recovery requires an accepted-record reader")
            records = await self.log.get_accepted_records(ids)
            if len(records) != len(ids):
                raise RuntimeFencedError("Invalid accepted-record recovery response")
            sources = {
                key: (record.document, record.provenance)
                for key, record in zip(ids, records, strict=True)
            }
        else:
            documents = await self.log.get_documents(ids)
            if len(documents) != len(ids):
                raise RuntimeFencedError("Invalid source recovery response")
            sources = {key: (document, None) for key, document in zip(ids, documents, strict=True)}
        for pointer in row["effects"]:
            await asyncio.sleep(0)  # Honour the deadline between bounded deterministic plans.
            if pointer["event_generation"] != digest(
                [pointer["event_id"], pointer["bundle"], pointer["effect_digest"]]
            ):
                return await self.graph.settle_relationship_intent(
                    row["node_id"], row["generation"], "invalid_intent"
                )
            edge = self._rederive(row, pointer, sources[pointer["event_id"]])
            if isinstance(edge, str):
                return await self.graph.settle_relationship_intent(
                    row["node_id"], row["generation"], edge
                )
            for name, value in edge.properties.items():
                if value is not None and name in pointer["writes"]:
                    removals.discard(name)
            properties.update(
                {
                    name: value
                    for name, value in edge.properties.items()
                    if value is not None and name in pointer["writes"]
                }
            )
            for name in edge.remove_properties:
                if name in pointer["writes"]:
                    properties.pop(name, None)
                    removals.add(name)
        insert = EdgeWrite(
            row["edge_type"],
            NodeRef(**row["source"]),
            NodeRef(**row["target"]),
            properties,
            create_only=not bool(row.get("write_modes")),
            remove_properties=tuple(sorted(removals)),
        )
        return await self.graph.settle_relationship_intent(
            row["node_id"], row["generation"], "waiting", insert
        )

    def _rederive(
        self,
        row: dict[str, Any],
        pointer: dict[str, Any],
        source: tuple[dict[str, Any] | None, VerifiedSourceProvenance | None],
    ) -> EdgeWrite | str:
        if pointer["authority"] != self.projector.authority_fingerprint:
            return "changed_authority"
        document, provenance = source
        if document is None:
            return "missing_source"
        try:
            event = Event.model_validate(document, strict=False)
            if str(event.event_id) != pointer["event_id"]:
                return "changed_source"
            event = event.model_copy(update={"global_position": pointer["position"]})
            plan = self.projector.plan(event, document, provenance=provenance)
        except (ValueError, TypeError):
            return (
                "changed_bundle"
                if pointer["bundle"] != self.projector.registry.version
                else "changed_source"
            )
        if (
            pointer.get("source_id") != plan.source_id
            or pointer.get("source_digest") != plan.source_digest
        ):
            return "changed_source"
        if pointer.get("plan_digest") != relationship_plan_digest(plan):
            return "changed_bundle" if pointer["bundle"] != plan.bundle else "changed_source"
        edges: list[tuple[EdgeWrite, str | None]] = [(edge, None) for edge in plan.edges]
        # Re-derive properties while retaining the originally selected references.
        from context_graph.worker.pack_projection import _edges

        for lookup in plan.lookups:
            selector = semantic_digest(effect_descriptor(lookup))
            if lookup.edge_type != row["edge_type"] or selector != pointer.get("selector_digest"):
                continue
            known = row["target"] if lookup.reverse else row["source"]
            found = row["source"] if lookup.reverse else row["target"]
            if asdict(lookup.known) == known and lookup.label == found["label"]:
                edges.extend(
                    (edge, selector)
                    for edge in _edges(lookup, [{lookup.key_property: found["key"]}])
                )
        matching = [
            edge
            for edge, selector in edges
            if edge_identity(edge) == [row["edge_type"], row["source"], row["target"]]
            and effect_digest(edge, selector) == pointer["effect_digest"]
        ]
        if matching:
            return matching[-1]
        return "changed_bundle" if pointer["bundle"] != plan.bundle else "changed_source"

    async def page(self, limit: int = 100) -> RecoveryReport:
        try:
            async with asyncio.timeout(self.timeout_s):
                return await self._page(limit)
        except TimeoutError:
            return RecoveryReport(complete_scan=False)

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
            await asyncio.sleep(0)
            status = await self._recover(row)
            report.scanned += 1
            if status not in TERMINAL:
                report.waiting += 1
                report.blocking += int(row["required"] or status != "endpoint_missing")
                if status == "superseded":
                    report.complete_scan = False
        return report

    async def finish(self, budget: int = 10_000, page_size: int = 100) -> RecoveryReport:
        try:
            async with asyncio.timeout(self.timeout_s):
                return await self._finish(budget, page_size)
        except TimeoutError:
            return RecoveryReport(complete_scan=False)

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
            report.complete_scan = report.complete_scan and part.complete_scan
            after = rows[-1]["node_id"]
        report.complete_scan = report.complete_scan and not bool(
            await self.graph.relationship_intents(after, 1)
        )
        return report
