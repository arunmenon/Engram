"""Neo4j implementation of the PackGraph operations (ADR-0018 decision 7).

Labels, relationship types and property keys are interpolated into Cypher
(Neo4j cannot parameterise them). They come from the ontology registry,
whose names have a fixed shape, and are checked again here, so nothing
else can reach the query text. Values are always parameters.

Source: ADR-0018
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

import orjson

from context_graph.adapters.graph_ops import LABEL_KEYS
from context_graph.adapters.neo4j.ontology_schema import schema_statements
from context_graph.domain.ontology import EDGE_TYPE_NAME, NODE_TYPE_NAME, PROPERTY_NAME
from context_graph.ports.errors import InvalidRequestError

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.ports.pack_graph import (
        Direction,
        EdgeWrite,
        NodeRef,
        NodeWrite,
        StateChange,
    )

# Edges read per neighbors() call before sorting and cutting to the limit
NEIGHBOR_SCAN_CAP = 10_000


def _label(name: str) -> str:
    if not NODE_TYPE_NAME.match(name):
        msg = f"invalid node label {name!r}"
        raise InvalidRequestError(msg)
    return name


def _edge_type(name: str) -> str:
    if not EDGE_TYPE_NAME.match(name):
        msg = f"invalid edge type {name!r}"
        raise InvalidRequestError(msg)
    return name


def _property(name: str) -> str:
    if not PROPERTY_NAME.match(name):
        msg = f"invalid property name {name!r}"
        raise InvalidRequestError(msg)
    return name


def _value(value: Any) -> Any:
    """Neo4j stores primitives and lists of them; nested maps become JSON text."""
    if isinstance(value, dict):
        return orjson.dumps(value).decode()
    if isinstance(value, list) and any(isinstance(item, dict | list) for item in value):
        return orjson.dumps(value).decode()
    return value


def _props(values: dict[str, Any]) -> dict[str, Any]:
    return {_property(k): _value(v) for k, v in values.items() if v is not None}


def _key_of(label: str, props: dict[str, Any]) -> Any:
    return props.get(LABEL_KEYS.get(label, "node_id"))


class Neo4jPackGraph:
    """PackGraph over a Neo4j driver; mixed into ``Neo4jGraphStore``."""

    _driver: AsyncDriver
    _database: str

    async def _pack_write(self, statements: list[tuple[str, dict[str, Any]]]) -> list[int]:
        """Run statements in one write transaction; each returns one count."""

        async def work(tx: Any) -> list[int]:
            counts: list[int] = []
            for query, params in statements:
                record = await (await tx.run(query, params)).single()
                counts.append(int(record[0]) if record else 0)
            return counts

        async with self._driver.session(database=self._database) as session:
            result: list[int] = await session.execute_write(work)
            return result

    async def _pack_read(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, params)
            return [record.data() async for record in result]

    async def ensure_pack_schema(
        self, registry: OntologyRegistry, embedding_dimensions: int
    ) -> None:
        statements = schema_statements(registry, embedding_dimensions)
        async with self._driver.session(database=self._database) as session:
            for statement in statements:
                await session.run(statement)

    async def upsert_nodes(self, writes: list[NodeWrite]) -> None:
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for write in writes:
            label, key_property = _label(write.ref.label), _property(write.ref.key_property)
            groups[(label, key_property)].append(
                {
                    "key": write.ref.key,
                    "props": _props(write.properties),
                    "defaults": _props(write.defaults),
                }
            )
        statements = [
            (
                f"UNWIND $rows AS row MERGE (n:{label} {{{key_property}: row.key}}) "
                "ON CREATE SET n += row.defaults SET n += row.props RETURN count(n)",
                {"rows": rows},
            )
            for (label, key_property), rows in groups.items()
        ]
        if statements:
            await self._pack_write(statements)

    async def upsert_edges(self, writes: list[EdgeWrite]) -> int:
        groups: dict[tuple[str, str, str, str, str, bool], list[dict[str, Any]]] = defaultdict(list)
        for write in writes:
            group = (
                _label(write.source.label),
                _property(write.source.key_property),
                _edge_type(write.edge_type),
                _label(write.target.label),
                _property(write.target.key_property),
                write.create_only,
            )
            groups[group].append(
                {
                    "source": write.source.key,
                    "target": write.target.key,
                    "props": _props(write.properties),
                }
            )
        statements = [
            (
                f"UNWIND $rows AS row MATCH (a:{source} {{{source_key}: row.source}}) "
                f"MATCH (b:{target} {{{target_key}: row.target}}) "
                f"MERGE (a)-[r:{edge_type}]->(b) {'ON CREATE SET' if create_only else 'SET'} "
                "r += row.props RETURN count(r)",
                {"rows": rows},
            )
            for (source, source_key, edge_type, target, target_key, create_only), rows in (
                groups.items()
            )
        ]
        return sum(await self._pack_write(statements)) if statements else 0

    async def change_states(self, changes: list[StateChange]) -> int:
        # One statement per change, in order, so later changes see earlier ones
        statements = [
            (
                f"MATCH (n:{_label(c.ref.label)} {{{_property(c.ref.key_property)}: $key}}) "
                "WHERE coalesce(n.status, '') <> $to "
                "AND (size($only_from) = 0 OR n.status IN $only_from) "
                "SET n.status = $to, n.status_changed_at = $changed_at RETURN count(n)",
                {
                    "key": c.ref.key,
                    "to": c.to_state,
                    "only_from": list(c.only_from),
                    "changed_at": c.changed_at,
                },
            )
            for c in changes
        ]
        return sum(await self._pack_write(statements)) if statements else 0

    async def get_nodes(self, refs: list[NodeRef]) -> dict[NodeRef, dict[str, Any]]:
        groups: dict[tuple[str, str], list[NodeRef]] = defaultdict(list)
        for ref in refs:
            groups[(_label(ref.label), _property(ref.key_property))].append(ref)
        found: dict[NodeRef, dict[str, Any]] = {}
        for (label, key_property), group in groups.items():
            by_key = {ref.key: ref for ref in group}
            rows = await self._pack_read(
                f"UNWIND $keys AS key MATCH (n:{label} {{{key_property}: key}}) "
                "RETURN key, properties(n) AS props",
                {"keys": list(by_key)},
            )
            for row in rows:
                found[by_key[row["key"]]] = row["props"]
        return found

    async def find_nodes(
        self, label: str, equals: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
        conditions = " AND ".join(f"n.{_property(k)} = $equals.{k}" for k in equals) or "true"
        key = _property(LABEL_KEYS.get(label, "node_id"))
        rows = await self._pack_read(
            f"MATCH (n:{_label(label)}) WHERE {conditions} RETURN properties(n) AS props "
            f"ORDER BY toString(n.{key}) LIMIT $limit",
            {"equals": {k: _value(v) for k, v in equals.items()}, "limit": limit},
        )
        return [row["props"] for row in rows]

    async def find_nodes_matching(
        self, label: str, conditions: list[dict[str, Any]], limit: int
    ) -> list[list[dict[str, Any]]]:
        if not conditions:
            return []
        fields = sorted(conditions[0])
        where = " AND ".join(f"n.{_property(k)} = c.values.{k}" for k in fields) or "true"
        key = _property(LABEL_KEYS.get(label, "node_id"))
        rows = await self._pack_read(
            f"UNWIND $conditions AS c MATCH (n:{_label(label)}) WHERE {where} "
            f"WITH c, n ORDER BY toString(n.{key}) "
            "WITH c.index AS index, collect(properties(n))[..$limit] AS props "
            "RETURN index, props",
            {
                "conditions": [
                    {"index": i, "values": {k: _value(v) for k, v in condition.items()}}
                    for i, condition in enumerate(conditions)
                ],
                "limit": limit,
            },
        )
        answers: list[list[dict[str, Any]]] = [[] for _ in conditions]
        for row in rows:
            answers[row["index"]] = list(row["props"])
        return answers

    async def find_latest(
        self, label: str, equals: dict[str, Any], order_by: str, not_after: str | None
    ) -> dict[str, Any] | None:
        conditions = [f"n.{_property(k)} = $equals.{k}" for k in equals]
        order = _property(order_by)
        conditions.append(f"n.{order} IS NOT NULL")
        if not_after is not None:
            conditions.append(f"toString(n.{order}) <= $not_after")
        key = _property(LABEL_KEYS.get(label, "node_id"))
        rows = await self._pack_read(
            f"MATCH (n:{_label(label)}) WHERE {' AND '.join(conditions)} "
            f"RETURN properties(n) AS props "
            f"ORDER BY toString(n.{order}) DESC, toString(n.{key}) DESC LIMIT 1",
            {"equals": {k: _value(v) for k, v in equals.items()}, "not_after": not_after},
        )
        return rows[0]["props"] if rows else None

    async def search_nodes(
        self, label: str, fields: list[str], terms: list[str], limit: int
    ) -> list[tuple[dict[str, Any], int]]:
        if not terms or not fields:
            return []
        key = LABEL_KEYS.get(label, "node_id")
        rows = await self._pack_read(
            f"MATCH (n:{_label(label)}) "
            "WITH n, [t IN $terms WHERE any(f IN $fields WHERE "
            "(n[f] IS :: STRING AND toLower(n[f]) CONTAINS t) OR "
            "(n[f] IS :: LIST<STRING> AND any(x IN n[f] WHERE toLower(x) CONTAINS t)))] AS hits "
            f"WHERE size(hits) > 0 RETURN properties(n) AS props, size(hits) AS hits "
            f"ORDER BY hits DESC, n.{_property(key)} LIMIT $limit",
            {"terms": terms, "fields": [_property(f) for f in fields], "limit": limit},
        )
        return [(row["props"], int(row["hits"])) for row in rows]

    async def neighbors(
        self,
        refs: list[NodeRef],
        edge_types: list[str] | None,
        direction: Direction,
        limit: int,
    ) -> list[dict[str, Any]]:
        types = [_edge_type(t) for t in edge_types] if edge_types is not None else None
        patterns = {"out": ["(n)-[r]->(m)"], "in": ["(n)<-[r]-(m)"]}
        wanted = patterns.get(direction, patterns["out"] + patterns["in"])
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for ref in refs:
            groups[(_label(ref.label), _property(ref.key_property))].append(ref.key)
        wanted_nodes = {(ref.label, ref.key) for ref in refs}
        rows: dict[tuple[Any, ...], dict[str, Any]] = {}
        for (label, key_property), keys in groups.items():
            for pattern in wanted:
                outgoing = pattern.endswith("->(m)")
                found = await self._pack_read(
                    f"UNWIND $keys AS key MATCH (n:{label} {{{key_property}: key}}) "
                    f"MATCH {pattern} WHERE $types IS NULL OR type(r) IN $types "
                    "RETURN type(r) AS edge_type, properties(r) AS properties, "
                    "labels(n)[0] AS n_label, properties(n) AS n_props, "
                    "labels(m)[0] AS m_label, properties(m) AS m_props LIMIT $cap",
                    {"keys": keys, "types": types, "cap": NEIGHBOR_SCAN_CAP},
                )
                for row in found:
                    near = (row["n_label"], _key_of(row["n_label"], row["n_props"]))
                    far = (row["m_label"], _key_of(row["m_label"], row["m_props"]))
                    source, target = (near, far) if outgoing else (far, near)
                    props = {near: row["n_props"], far: row["m_props"]}
                    # The other end, as graph_ops reports it when both ends were asked for
                    other = (
                        target
                        if (source[0], str(source[1])) in wanted_nodes and direction != "in"
                        else source
                    )
                    edge_key = (source, row["edge_type"], target)
                    rows.setdefault(
                        edge_key,
                        {
                            "edge_type": row["edge_type"],
                            "properties": row["properties"],
                            "source_label": source[0],
                            "source_key": source[1],
                            "target_label": target[0],
                            "target_key": target[1],
                            "node_label": other[0],
                            "node": props[other],
                        },
                    )
        ordered = sorted(
            rows.values(),
            key=lambda r: (
                r["edge_type"],
                (r["source_label"], str(r["source_key"])),
                (r["target_label"], str(r["target_key"])),
            ),
        )
        return ordered[:limit]
