"""Neo4j constraints and indexes generated from the ontology registry (ADR-0018).

For the ``core``, ``memory`` and ``user`` packs this reproduces
``docker/neo4j/constraints.cypher`` (checked by the pack tests); types
added by other packs get the same treatment:

- a uniqueness constraint ``<type>_pk`` on the type's ``id_property``,
  or on ``node_id`` for types identified by their key;
- a range index per declared index field;
- a cosine vector index on the declared vector property.

Labels and property names come from the registry, which only accepts
names of a fixed shape, rejects type names that differ only by case and
index fields that would reuse the ``_pk`` name, so names cannot collide
and nothing user-supplied reaches the statements.

Source: ADR-0018, ADR-0011 §7
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context_graph.domain.ontology import OntologyRegistry


def schema_statements(registry: OntologyRegistry, embedding_dimensions: int) -> list[str]:
    """``CREATE ... IF NOT EXISTS`` statements for every node type in the registry."""
    statements: list[str] = []
    for name, node_type in registry.node_types.items():
        lower = name.lower()
        definition = node_type.definition
        if definition.id_property:
            statements.append(
                f"CREATE CONSTRAINT {lower}_pk IF NOT EXISTS FOR (n:{name}) "
                f"REQUIRE n.{definition.id_property} IS UNIQUE"
            )
        else:
            statements.append(
                f"CREATE CONSTRAINT {lower}_pk IF NOT EXISTS FOR (n:{name}) "
                "REQUIRE n.node_id IS UNIQUE"
            )
    for name, node_type in registry.node_types.items():
        lower = name.lower()
        for field_name in node_type.definition.indexes:
            statements.append(
                f"CREATE INDEX {lower}_{field_name} IF NOT EXISTS "
                f"FOR (n:{name}) ON (n.{field_name})"
            )
    for name, node_type in registry.node_types.items():
        vector_property = node_type.definition.vector_property
        if vector_property:
            statements.append(
                f"CREATE VECTOR INDEX {name.lower()}_{vector_property}_idx IF NOT EXISTS "
                f"FOR (n:{name}) ON (n.{vector_property}) "
                "OPTIONS {indexConfig: {"
                f"`vector.dimensions`: {embedding_dimensions}, "
                "`vector.similarity_function`: 'cosine'}}"
            )
    return statements
