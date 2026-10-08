"""Explicit additive acceptance schema planning; startup never applies DDL."""

from context_graph.adapters.spanner.entity_index import table_columns

ACCEPTANCE_COLUMN_DDL = "ALTER TABLE Events ADD COLUMN acceptance JSON"


class AcceptanceSchemaError(RuntimeError):
    """Existing acceptance column is incompatible; no repair is attempted."""


def acceptance_column_valid(ddl: list[str]) -> bool:
    return table_columns(ddl, "Events").get("acceptance") == ("acceptance", "json")


def plan_acceptance_upgrade(ddl: list[str]) -> list[str]:
    columns = table_columns(ddl, "Events")
    if not columns:
        raise AcceptanceSchemaError("Events table is missing or unsupported")
    if "acceptance" not in columns:
        return [ACCEPTANCE_COLUMN_DDL]
    if not acceptance_column_valid(ddl):
        raise AcceptanceSchemaError("Events.acceptance must be nullable nongenerated JSON")
    return []
