"""Entity-only ANN definitions and explicit, additive upgrade (#44).

Startup validates these definitions; only an explicit admin caller upgrades.
Unknown physical definitions fail closed instead of being dropped or rewritten.
"""

from __future__ import annotations

import re
from typing import Any

ENTITY_VECTOR_INDEX = "GraphEntitiesByEmbeddingV1"
MEMBERSHIP_COLUMN = "entity_embedding_member"
MEMBERSHIP_DDL = "entity_embedding_member BOOL AS (IF(label = 'Entity', TRUE, NULL)) HIDDEN"
ENTITY_INDEX_DDL = (
    f"CREATE VECTOR INDEX {ENTITY_VECTOR_INDEX} ON GraphNodes (embedding) "
    "STORING (entity_embedding_member) "
    "WHERE embedding IS NOT NULL AND entity_embedding_member IS NOT NULL "
    "OPTIONS (distance_type = 'COSINE')"
)


def _tokens(sql: str) -> tuple[str, ...]:
    """Normalize supported DDL while preserving case-sensitive literals."""
    pattern = (
        r"\s+|`[^`]+`|'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|[A-Za-z_][A-Za-z_0-9]*|\d+|=>|[(),;=<>]"
    )
    parts = re.findall(pattern, sql)
    if "".join(parts) != sql:
        return ()
    normalized = []
    for token in parts:
        if token.isspace():
            continue
        if token.startswith(("'", '"')):
            normalized.append("'" + token[1:-1] + "'")
        else:
            normalized.append(token.strip("`").lower())
    return tuple(normalized)


def _flat(tokens: tuple[str, ...]) -> tuple[str, ...]:
    # The accepted grammar contains only IF's three arguments and an AND
    # conjunction. Extra operators/tokens remain visible and are rejected.
    return tuple(t for t in tokens if t not in ("(", ")", ";"))


def ddl_statement_matches(expected: str, observed: str) -> bool:
    """Match RPC DDL formatting without discarding operators or literal case."""
    tokens = _tokens(expected)
    return bool(tokens) and tokens == _tokens(observed)


def table_columns(ddl: list[str]) -> dict[str, tuple[str, ...]]:
    for statement in ddl:
        tokens = _tokens(statement)
        if tokens[:4] != ("create", "table", "graphnodes", "("):
            continue
        columns, start, depth = {}, 4, 0
        for i in range(4, len(tokens)):
            token = tokens[i]
            if token == ")" and depth == 0:
                if i > start:
                    columns[tokens[start]] = tokens[start:i]
                return columns
            if token == "," and depth == 0:
                columns[tokens[start]] = tokens[start:i]
                start = i + 1
            elif token == "(":
                depth += 1
            elif token == ")":
                depth -= 1
    return {}


def membership_valid(columns: dict[str, tuple[str, ...]]) -> bool:
    return _flat(columns.get(MEMBERSHIP_COLUMN, ())) == _flat(_tokens(MEMBERSHIP_DDL))


def index_definition(ddl: list[str]) -> str | None:
    for statement in ddl:
        tokens = _tokens(statement)
        # Include ordinary/search indexes so an incompatible name collision
        # cannot be treated as an absent index by the upgrade planner.
        if tokens[:1] == ("create",) and "index" in tokens[:3]:
            pos = tokens.index("index")
            if tokens[pos + 1 : pos + 2] == (ENTITY_VECTOR_INDEX.lower(),):
                return statement
    return None


def index_valid(statement: str | None) -> bool:
    actual = _flat(_tokens(statement or ""))
    expected = _flat(_tokens(ENTITY_INDEX_DDL))
    reverse = ENTITY_INDEX_DDL.replace(
        "embedding IS NOT NULL AND entity_embedding_member IS NOT NULL",
        "entity_embedding_member IS NOT NULL AND embedding IS NOT NULL",
    )
    return actual in (expected, _flat(_tokens(reverse)))


class EntityIndexUpgradeError(RuntimeError):
    """Unsafe/incompatible physical state or incomplete upgrade."""


class PendingEntityIndexUpgradeError(EntityIndexUpgradeError):
    """Inspect these live operations before attempting another upgrade."""

    def __init__(self, operation_names: list[str]) -> None:
        self.operation_names = operation_names
        super().__init__(f"Spanner DDL pending; inspect operations: {operation_names}")


def plan_entity_index_upgrade(database: Any, dimensions: int) -> list[str]:
    """Read-only plan independent of the target startup handshake."""
    database.reload()
    ddl = list(database.ddl_statements)
    columns = table_columns(ddl)
    expected_embedding = _tokens(f"embedding ARRAY<FLOAT64>(vector_length=>{dimensions})")
    if columns.get("embedding") != expected_embedding:
        raise EntityIndexUpgradeError("GraphNodes embedding definition/dimensions incompatible")
    plan = []
    if MEMBERSHIP_COLUMN in columns:
        if not membership_valid(columns):
            raise EntityIndexUpgradeError("Entity membership column has incompatible semantics")
    else:
        plan.append(f"ALTER TABLE GraphNodes ADD COLUMN {MEMBERSHIP_DDL}")
    index = index_definition(ddl)
    if index is None:
        plan.append(ENTITY_INDEX_DDL)
    elif not index_valid(index):
        raise EntityIndexUpgradeError("Entity vector index has incompatible semantics")
    return plan
