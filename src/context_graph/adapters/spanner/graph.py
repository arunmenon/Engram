"""Spanner graph backend (ADR-0019 step 4, design brief D4).

The projection lives in schemaless ``GraphNodes`` / ``GraphEdges`` tables
(JSON properties, dynamic labels) with a ``CREATE PROPERTY GRAPH`` over
them, so a new ontology pack needs no DDL. Every ``GraphBackend`` method
comes from ``adapters.graph_ops.GraphOperations``; this module supplies
its storage primitives as key-range reads, index reads and mutations, and
two native fast paths:

- entity similarity uses the cosine vector index
  (``APPROX_COSINE_DISTANCE``), scored ``1 - distance / 2`` = Neo4j's
  ``(1 + cosine) / 2``;
- lineage uses a Spanner Graph GQL ``TRAIL`` quantified path, the
  equivalent of Neo4j's ``-[:CAUSED_BY*1..10]->`` with edge uniqueness.

Writes that read-modify-write (MERGE then SET) run in read-write
transactions sized by a ``CommitBudget`` (``adapters.spanner.commits``):
a primitive call's items are grouped by key, the groups are packed into
commit-sized runs, and a run whose rows turn out larger than estimated
(existing properties are only known inside the transaction) is split in
two and retried. One key's items always share a transaction.

Source: ADR-0009, ADR-0018, ADR-0019, spanner-design-brief.md D4/G8/G9/G10
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from context_graph.adapters.errors import translate_errors
from context_graph.adapters.graph_ops import (
    LINEAGE_MAX_HOPS,
    EdgeKey,
    EdgeRow,
    GraphOperationReads,
    GraphOperations,
    NodeKey,
    apply_set,
    key_property,
    state_change_applies,
)
from context_graph.adapters.spanner.commits import (
    EDGE_DELETE_MUTATIONS,
    NODE_DELETE_MUTATIONS,
    CommitBudget,
    CommitTooLarge,
    edge_row_cost,
    group_by_key,
    node_row_cost,
)
from context_graph.adapters.spanner.errors import translate_spanner_error
from context_graph.adapters.spanner.log import json_param, json_value

if TYPE_CHECKING:
    from collections.abc import Callable

    from context_graph.ports.pack_graph import StateChange
    from context_graph.settings import DecaySettings, PPRSettings

NODE_COLUMNS = ["label", "node_id", "props", "embedding"]
EDGE_COLUMNS = ["src_label", "src_id", "edge_type", "dst_label", "dst_id", "props"]

# Approximate vector search breadth (Spanner's num_leaves_to_search option)
VECTOR_LEAVES_TO_SEARCH = 10
VECTOR_SEARCH_OPTIONS = f'{{"num_leaves_to_search": {VECTOR_LEAVES_TO_SEARCH}}}'


def _edge_row(row: list[Any]) -> EdgeRow:
    src_label, src_id, edge_type, dst_label, dst_id, props = row
    return ((src_label, src_id), edge_type, (dst_label, dst_id)), json_value(props) or {}


class SpannerGraphReads(GraphOperationReads):
    """``GraphReads`` with a Spanner Graph (GQL) fast path for lineage."""

    def __init__(self, store: SpannerGraphStore) -> None:
        super().__init__(store)
        self._store = store

    async def lineage_chains(
        self,
        node_id: str,
        max_depth: int,
        max_nodes: int,
        *,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        from google.cloud.spanner_v1 import param_types

        hop_limit = min(max_depth, LINEAGE_MAX_HOPS)
        if hop_limit < 1:
            return []
        # One row per path: the node ids along it, start to ancestor.
        # Labels are matched on the key columns, not as `:Event` / `:CAUSED_BY`:
        # on a real instance a dynamic-label filter matched nothing while
        # LABELS() listed the label (trial of 2026-10-05); the emulator
        # matched both ways.
        rows = await self._store._query(
            "GRAPH EngramGraph "
            # The bound is an int we computed, so inlining it is safe.
            "MATCH p = TRAIL (start)-[e WHERE e.edge_type = 'CAUSED_BY']->"
            f"{{1,{int(hop_limit)}}}(ancestor) "
            "WHERE start.label = 'Event' AND start.node_id = @node_id "
            "RETURN ARRAY(SELECT n.node_id FROM UNNEST(NODES(p)) AS n WITH OFFSET o "
            "ORDER BY o) AS ids "
            "LIMIT @limit",
            {"node_id": node_id, "limit": max_nodes},
            {"node_id": param_types.STRING, "limit": param_types.INT64},
        )
        paths = [list(zip(row[0][:-1], row[0][1:], strict=True)) for row in rows]
        edge_keys: list[EdgeKey] = sorted(
            {(("Event", src), "CAUSED_BY", ("Event", dst)) for path in paths for src, dst in path}
        )
        edge_props = {key: props for key, props in await self._store._edge_rows_by_key(edge_keys)}
        node_keys = sorted({("Event", node_id)} | {k[2] for k in edge_keys})
        nodes = await self._store._get_nodes(node_keys)
        chains = []
        for path in paths:
            ids = [node_id] + [dst for _src, dst in path]
            chains.append(
                {
                    "nodes": [dict(nodes.get(("Event", i), {})) for i in ids],
                    "edges": [
                        {
                            "source": src,
                            "target": dst,
                            "properties": dict(
                                edge_props.get((("Event", src), "CAUSED_BY", ("Event", dst)), {})
                            ),
                        }
                        for src, dst in path
                    ],
                }
            )
        return chains


@translate_errors(translate_spanner_error)
class SpannerGraphStore(GraphOperations):
    """``GraphBackend`` over Spanner tables and Spanner Graph."""

    def __init__(
        self,
        database: Any,
        *,
        embedding_dimensions: int = 384,
        decay_settings: DecaySettings | None = None,
        ppr_settings: PPRSettings | None = None,
        commit_budget: CommitBudget | None = None,
    ) -> None:
        super().__init__(
            decay_settings=decay_settings,
            ppr_settings=ppr_settings,
            provenance_source="spanner",
        )
        self._database = database
        self._dimensions = embedding_dimensions
        self._budget = commit_budget or CommitBudget()
        self._reads = SpannerGraphReads(self)

    # ------------------------------------------------------------------
    # Client helpers (the Google client is synchronous: run in threads)
    # ------------------------------------------------------------------

    async def _query(
        self, sql: str, params: dict[str, Any] | None = None, types: dict[str, Any] | None = None
    ) -> list[list[Any]]:
        def query() -> list[list[Any]]:
            with self._database.snapshot() as snapshot:
                return [
                    list(row) for row in snapshot.execute_sql(sql, params=params, param_types=types)
                ]

        rows: list[list[Any]] = await asyncio.to_thread(query)
        return rows

    async def _read(
        self, table: str, columns: list[str], keyset: Any, index: str = ""
    ) -> list[list[Any]]:
        def read() -> list[list[Any]]:
            with self._database.snapshot() as snapshot:
                return [list(row) for row in snapshot.read(table, columns, keyset, index=index)]

        rows: list[list[Any]] = await asyncio.to_thread(read)
        return rows

    async def _transact(self, fn: Any) -> Any:
        return await asyncio.to_thread(self._database.run_in_transaction, fn)

    async def _write_in_commits(
        self,
        groups: list[list[Any]],
        estimate: Callable[[list[Any]], tuple[int, int]],
        write: Callable[[list[Any], bool], Callable[[Any], Any]],
    ) -> list[Any]:
        """Write key groups in commit-sized transactions; each transaction's result.

        ``write(items, enforce)`` returns the transaction body. With
        ``enforce`` it raises ``CommitTooLarge`` once it knows its rows
        exceed the budget, and the run is split in two and retried. A run
        of one group is written whatever its size.
        """
        pending = self._budget.chunks(groups, estimate)
        results = []
        while pending:
            run = pending.pop(0)
            items = [item for group in run for item in group]
            try:
                results.append(await self._transact(write(items, len(run) > 1)))
            except CommitTooLarge:
                middle = len(run) // 2
                pending[:0] = [run[:middle], run[middle:]]
        return results

    def _node_rows(
        self, nodes: dict[NodeKey, dict[str, Any]], keys: Any, enforce: bool
    ) -> list[list[Any]]:
        """GraphNodes rows for ``keys``; with ``enforce``, checked against the budget."""
        rows = []
        costs = []
        for label, node_id in keys:
            props = nodes[(label, node_id)]
            embedding = self._embedding_column(label, props)
            rows.append([label, node_id, json_param(props), embedding])
            costs.append(node_row_cost((label, node_id), props, embedding))
        if enforce:
            self._budget.check(costs)
        return rows

    @staticmethod
    def _node_estimate(group: list[Any]) -> tuple[int, int]:
        """Cost of a node key's writes before its stored properties are read."""
        key = group[0][0]
        return node_row_cost(key, {k: v for item in group for k, v in item[1].items()}, None)

    @staticmethod
    def _prefix_keyset(prefixes: list[list[Any]]) -> Any:
        from google.cloud.spanner_v1 import KeyRange, KeySet

        return KeySet(
            ranges=[KeyRange(start_closed=prefix, end_closed=prefix) for prefix in prefixes]
        )

    def _embedding_column(self, label: str, props: dict[str, Any]) -> list[float] | None:
        embedding = props.get("embedding")
        if label != "Entity" or not embedding or len(embedding) != self._dimensions:
            return None
        return [float(v) for v in embedding]

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------

    async def _get_nodes(self, keys: list[NodeKey]) -> dict[NodeKey, dict[str, Any]]:
        from google.cloud.spanner_v1 import KeySet

        unique = sorted(set(keys))
        if not unique:
            return {}
        rows = await self._read(
            "GraphNodes",
            ["label", "node_id", "props"],
            KeySet(keys=[list(key) for key in unique]),
        )
        return {(label, node_id): json_value(props) for label, node_id, props in rows}

    async def _find_nodes(
        self, label: str, where: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        from google.cloud.spanner_v1 import param_types

        conditions = dict(where or {})
        if "session_id" in conditions and conditions["session_id"] is not None:
            rows = await self._query(
                "SELECT props FROM GraphNodes@{FORCE_INDEX=GraphNodesBySession} "
                "WHERE label = @label AND session_id = @session_id",
                {"label": label, "session_id": conditions.pop("session_id")},
                {"label": param_types.STRING, "session_id": param_types.STRING},
            )
            nodes = [json_value(row[0]) for row in rows]
        else:
            rows = await self._read("GraphNodes", ["props"], self._prefix_keyset([[label]]))
            nodes = [json_value(row[0]) for row in rows]
        return [
            props
            for props in nodes
            if all(props.get(name) == value for name, value in conditions.items())
        ]

    async def _upsert_nodes(self, items: list[tuple[NodeKey, dict[str, Any]]]) -> None:
        from google.cloud.spanner_v1 import KeySet

        if not items:
            return

        def write(run: list[tuple[NodeKey, dict[str, Any]]], enforce: bool) -> Any:
            def work(transaction: Any) -> None:
                keys = sorted({key for key, _updates in run})
                current = {
                    (label, node_id): json_value(props)
                    for label, node_id, props in transaction.read(
                        "GraphNodes",
                        ["label", "node_id", "props"],
                        KeySet(keys=[list(key) for key in keys]),
                    )
                }
                for (label, node_id), updates in run:
                    props = current.setdefault((label, node_id), {key_property(label): node_id})
                    apply_set(props, updates)
                transaction.insert_or_update(
                    "GraphNodes", NODE_COLUMNS, self._node_rows(current, current, enforce)
                )

            return work

        await self._write_in_commits(
            group_by_key(items, lambda item: item[0]), self._node_estimate, write
        )

    async def _merge_nodes(
        self, items: list[tuple[NodeKey, dict[str, Any], dict[str, Any]]]
    ) -> None:
        """MERGE with create-only defaults, read and written in one transaction per run."""
        from google.cloud.spanner_v1 import KeySet

        if not items:
            return

        def write(run: list[tuple[NodeKey, dict[str, Any], dict[str, Any]]], enforce: bool) -> Any:
            def work(transaction: Any) -> None:
                keys = sorted({key for key, _u, _d in run})
                current = {
                    (label, node_id): json_value(props)
                    for label, node_id, props in transaction.read(
                        "GraphNodes",
                        ["label", "node_id", "props"],
                        KeySet(keys=[list(key) for key in keys]),
                    )
                }
                for (label, node_id), updates, defaults in run:
                    props = current.get((label, node_id))
                    if props is None:
                        props = current[(label, node_id)] = {
                            key_property(label): node_id,
                            **defaults,
                        }
                    apply_set(props, updates)
                transaction.insert_or_update(
                    "GraphNodes", NODE_COLUMNS, self._node_rows(current, current, enforce)
                )

            return work

        await self._write_in_commits(
            group_by_key(items, lambda item: item[0]),
            lambda group: node_row_cost(
                group[0][0], {k: v for _key, u, d in group for k, v in (d | u).items()}, None
            ),
            write,
        )

    async def _apply_state_changes(self, changes: list[StateChange]) -> int:
        """Apply transitions in order; one node's transitions share a transaction."""
        from google.cloud.spanner_v1 import KeySet

        if not changes:
            return 0

        def write(run: list[StateChange], enforce: bool) -> Any:
            def work(transaction: Any) -> int:
                keys = sorted({(c.ref.label, c.ref.key) for c in run})
                current = {
                    (label, node_id): json_value(props)
                    for label, node_id, props in transaction.read(
                        "GraphNodes",
                        ["label", "node_id", "props"],
                        KeySet(keys=[list(key) for key in keys]),
                    )
                }
                changed: set[NodeKey] = set()
                count = 0
                for change in run:
                    key = (change.ref.label, change.ref.key)
                    props = current.get(key)
                    if not state_change_applies(props, change):
                        continue
                    assert props is not None
                    props["status"] = change.to_state
                    props["status_changed_at"] = change.changed_at
                    changed.add(key)
                    count += 1
                if changed:
                    rows = self._node_rows(current, sorted(changed), enforce)
                    transaction.update("GraphNodes", NODE_COLUMNS, rows)
                return count

            return work

        counts = await self._write_in_commits(
            group_by_key(changes, lambda change: (change.ref.label, change.ref.key)),
            lambda group: node_row_cost((group[0].ref.label, group[0].ref.key), {}, None),
            write,
        )
        return sum(counts)

    def _incident_edges_sync(self, transaction: Any, keys: list[NodeKey]) -> list[list[Any]]:
        prefixes = [list(key) for key in keys]
        outgoing = transaction.read("GraphEdges", EDGE_COLUMNS[:5], self._prefix_keyset(prefixes))
        incoming = transaction.read(
            "GraphEdges",
            EDGE_COLUMNS[:5],
            self._prefix_keyset(prefixes),
            index="GraphEdgesByTarget",
        )
        return [list(row) for row in outgoing] + [list(row) for row in incoming]

    async def _delete_nodes(self, keys: list[NodeKey]) -> int:
        """Detach-delete nodes, in commit-sized transactions.

        A run whose incident edges would not fit in one commit deletes those
        edges first, in transactions of their own, and is then retried; the
        nodes and any edges added meanwhile go together.
        """
        from google.cloud.spanner_v1 import KeySet

        unique = sorted(set(keys))
        if not unique:
            return 0
        budget = self._budget.max_mutations
        deleted = 0
        for run in self._budget.chunks(unique, lambda _key: (NODE_DELETE_MUTATIONS, 0)):

            def work(transaction: Any, run: list[NodeKey] = run) -> int | list[list[Any]]:
                existing = [
                    (label, node_id)
                    for label, node_id in transaction.read(
                        "GraphNodes",
                        ["label", "node_id"],
                        KeySet(keys=[list(key) for key in run]),
                    )
                ]
                if not existing:
                    return 0
                edges = self._incident_edges_sync(transaction, existing)
                mutations = len(edges) * EDGE_DELETE_MUTATIONS
                if mutations + len(existing) * NODE_DELETE_MUTATIONS > budget:
                    return edges  # too many to delete with the nodes
                if edges:
                    transaction.delete("GraphEdges", KeySet(keys=edges))
                transaction.delete("GraphNodes", KeySet(keys=[list(key) for key in existing]))
                return len(existing)

            while True:
                outcome = await self._transact(work)
                if isinstance(outcome, int):
                    deleted += outcome
                    break
                await self._delete_edge_rows(outcome)
        return deleted

    async def _delete_edge_rows(self, rows: list[list[Any]]) -> None:
        """Delete GraphEdges rows by primary key, in commit-sized transactions."""
        from google.cloud.spanner_v1 import KeySet

        unique = sorted({tuple(row) for row in rows})
        for run in self._budget.chunks(unique, lambda _row: (EDGE_DELETE_MUTATIONS, 0)):

            def work(transaction: Any, run: list[tuple[Any, ...]] = run) -> None:
                transaction.delete("GraphEdges", KeySet(keys=[list(row) for row in run]))

            await self._transact(work)

    async def _edges(
        self,
        *,
        sources: list[NodeKey] | None = None,
        targets: list[NodeKey] | None = None,
        edge_type: str | None = None,
    ) -> list[EdgeRow]:
        from google.cloud.spanner_v1 import KeySet, param_types

        if (sources is not None and not sources) or (targets is not None and not targets):
            return []
        suffix = [edge_type] if edge_type is not None else []
        if sources is not None:
            rows = await self._read(
                "GraphEdges",
                EDGE_COLUMNS,
                self._prefix_keyset([[*key, *suffix] for key in sorted(set(sources))]),
            )
        elif targets is not None:
            rows = await self._read(
                "GraphEdges",
                EDGE_COLUMNS,
                self._prefix_keyset([[*key, *suffix] for key in sorted(set(targets))]),
                index="GraphEdgesByTarget",
            )
        elif edge_type is not None:
            rows = await self._query(
                "SELECT src_label, src_id, edge_type, dst_label, dst_id, props "
                "FROM GraphEdges@{FORCE_INDEX=GraphEdgesByType} WHERE edge_type = @edge_type",
                {"edge_type": edge_type},
                {"edge_type": param_types.STRING},
            )
        else:
            rows = await self._read("GraphEdges", EDGE_COLUMNS, KeySet(all_=True))
        edges = [_edge_row(row) for row in rows]
        target_set = set(targets) if targets is not None and sources is not None else None
        return [
            (key, props)
            for key, props in edges
            if (target_set is None or key[2] in target_set)
            and (edge_type is None or key[1] == edge_type)
        ]

    async def _edge_rows_by_key(self, keys: list[EdgeKey]) -> list[EdgeRow]:
        from google.cloud.spanner_v1 import KeySet

        if not keys:
            return []
        rows = await self._read(
            "GraphEdges",
            EDGE_COLUMNS,
            KeySet(keys=[[s[0], s[1], t, d[0], d[1]] for s, t, d in keys]),
        )
        return [_edge_row(row) for row in rows]

    async def _upsert_edges(self, items: list[tuple[EdgeKey, dict[str, Any]]]) -> int:
        from google.cloud.spanner_v1 import KeySet

        if not items:
            return 0
        budget = self._budget

        def write(run: list[tuple[EdgeKey, dict[str, Any]]], enforce: bool) -> Any:
            def work(transaction: Any) -> int:
                endpoints = sorted({key[0] for key, _u in run} | {key[2] for key, _u in run})
                existing_nodes = {
                    (label, node_id)
                    for label, node_id in transaction.read(
                        "GraphNodes",
                        ["label", "node_id"],
                        KeySet(keys=[list(key) for key in endpoints]),
                    )
                }
                wanted = sorted(
                    {
                        key
                        for key, _u in run
                        if key[0] in existing_nodes and key[2] in existing_nodes
                    }
                )
                if not wanted:
                    return 0
                current = {
                    key: props
                    for key, props in (
                        _edge_row(list(row))
                        for row in transaction.read(
                            "GraphEdges",
                            EDGE_COLUMNS,
                            KeySet(keys=[[s[0], s[1], t, d[0], d[1]] for s, t, d in wanted]),
                        )
                    )
                }
                wanted_set = set(wanted)
                for key, updates in run:
                    if key in wanted_set:
                        apply_set(current.setdefault(key, {}), updates)
                if enforce:
                    budget.check([edge_row_cost(key, props) for key, props in current.items()])
                transaction.insert_or_update(
                    "GraphEdges",
                    EDGE_COLUMNS,
                    [
                        [s[0], s[1], edge_type, d[0], d[1], json_param(props)]
                        for (s, edge_type, d), props in current.items()
                    ],
                )
                return len(wanted)

            return work

        counts = await self._write_in_commits(
            group_by_key(items, lambda item: item[0]),
            lambda group: edge_row_cost(
                group[0][0], {k: v for _key, updates in group for k, v in updates.items()}
            ),
            write,
        )
        return sum(counts)

    async def _delete_edges(self, keys: list[EdgeKey]) -> None:
        if not keys:
            return
        await self._delete_edge_rows([[s[0], s[1], t, d[0], d[1]] for s, t, d in keys])

    async def _clear(self) -> None:
        def clear() -> None:
            self._database.execute_partitioned_dml("DELETE FROM GraphEdges WHERE TRUE")
            self._database.execute_partitioned_dml("DELETE FROM GraphNodes WHERE TRUE")

        await asyncio.to_thread(clear)

    # ------------------------------------------------------------------
    # Native fast paths and lifecycle
    # ------------------------------------------------------------------

    async def search_similar_entities(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.75,
    ) -> list[dict[str, Any]]:
        from google.cloud.spanner_v1 import param_types

        if len(query_embedding) != self._dimensions:
            return await super().search_similar_entities(query_embedding, top_k, threshold)
        rows = await self._query(
            "SELECT node_id, props, APPROX_COSINE_DISTANCE(embedding, @query, "
            f"options => JSON '{VECTOR_SEARCH_OPTIONS}') AS distance "
            "FROM GraphNodes@{FORCE_INDEX=GraphNodesByEmbedding} "
            "WHERE embedding IS NOT NULL ORDER BY distance LIMIT @top_k",
            {"query": [float(v) for v in query_embedding], "top_k": top_k},
            {"query": param_types.Array(param_types.FLOAT64), "top_k": param_types.INT64},
        )
        results = []
        for node_id, props, distance in rows:
            score = max(0.0, min(1.0, 1.0 - float(distance) / 2.0))
            if score < threshold:
                continue
            values = json_value(props)
            results.append(
                {
                    "entity_id": node_id,
                    "name": values.get("name"),
                    "entity_type": values.get("entity_type"),
                    "score": score,
                }
            )
        return results

    async def health_ping(self) -> bool:
        try:
            await self._query("SELECT 1")
        except Exception:  # noqa: BLE001
            return False
        return True
