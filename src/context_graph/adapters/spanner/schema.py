"""Spanner schema and connection (ADR-0019 step 4, Spanner design brief §3).

One database holds the event ledger, the consumer-group state and the
graph projection. Ledger and graph still never share a transaction in
the write path: the graph is a derived, rebuildable projection (D5).

Layout choices, from the design brief:

- D1: a position is ``<commit timestamp>/<batch index>/<event id>``,
  fixed width, so positions sort as strings within one ledger;
- D3: the ledger is keyed by ``event_id`` (random UUIDs); the time index
  leads with ``shard = crc32(session_id) mod N`` so it has no monotonic
  hotspot and one session's events stay in one shard, in order;
- D4: the graph is schemaless ``GraphNodes`` / ``GraphEdges`` tables with
  JSON properties and a ``CREATE PROPERTY GRAPH`` over them, so a new
  ontology pack needs no DDL;
- keyword search uses a full-text search index; entity embeddings a
  cosine vector index.

Source: ADR-0019, docs/research/2026-10/ontology/spanner-design-brief.md
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from context_graph.settings import SpannerSettings

log = structlog.get_logger(__name__)

# Floor position for a consumer cursor that has delivered nothing yet
CURSOR_FLOOR_TIMESTAMP = "0001-01-01T00:00:00Z"


def schema_statements(embedding_dimensions: int) -> list[str]:
    """DDL for an empty database, in dependency order."""
    return [
        # -- Event ledger -------------------------------------------------
        """CREATE TABLE Events (
            event_id STRING(64) NOT NULL,
            shard INT64 NOT NULL,
            commit_ts TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp = true),
            batch_index INT64 NOT NULL,
            session_id STRING(MAX) NOT NULL,
            occurred_at_ms INT64 NOT NULL,
            session_tag STRING(MAX),
            agent_tag STRING(MAX),
            trace_tag STRING(MAX),
            event_type_tag STRING(MAX),
            tool_name_tag STRING(MAX),
            document JSON,
            legacy_position STRING(MAX),
            in_log BOOL NOT NULL,
            in_session_index BOOL NOT NULL,
            dedup_active BOOL NOT NULL,
            summary STRING(MAX),
            keywords STRING(MAX),
            search_text STRING(MAX),
            summary_tokens TOKENLIST AS (TOKENIZE_FULLTEXT(summary)) HIDDEN,
            keywords_tokens TOKENLIST AS (TOKENIZE_FULLTEXT(keywords)) HIDDEN,
            search_text_tokens TOKENLIST AS (TOKENIZE_FULLTEXT(search_text)) HIDDEN,
            text_tokens TOKENLIST AS (
                TOKENLIST_CONCAT([summary_tokens, keywords_tokens, search_text_tokens])
            ) HIDDEN
        ) PRIMARY KEY (event_id)""",
        "CREATE INDEX EventsByShardPosition ON Events (shard, commit_ts, batch_index)",
        "CREATE INDEX EventsBySession ON Events (session_id, commit_ts, batch_index)",
        "CREATE INDEX EventsBySessionTag ON Events (session_tag, occurred_at_ms)",
        "CREATE SEARCH INDEX EventsText ON Events (text_tokens) STORING (session_tag)",
        # -- Consumer groups (replace XREADGROUP / XPENDING / XAUTOCLAIM) --
        """CREATE TABLE ConsumerGroups (
            group_name STRING(MAX) NOT NULL,
            created_at TIMESTAMP NOT NULL
        ) PRIMARY KEY (group_name)""",
        """CREATE TABLE ConsumerCursors (
            group_name STRING(MAX) NOT NULL,
            shard INT64 NOT NULL,
            commit_ts TIMESTAMP NOT NULL,
            batch_index INT64 NOT NULL,
            event_id STRING(64) NOT NULL
        ) PRIMARY KEY (group_name, shard)""",
        """CREATE TABLE ConsumerDeliveries (
            group_name STRING(MAX) NOT NULL,
            event_id STRING(64) NOT NULL,
            consumer STRING(MAX) NOT NULL,
            delivery_count INT64 NOT NULL,
            last_delivered_at TIMESTAMP NOT NULL,
            commit_ts TIMESTAMP NOT NULL,
            batch_index INT64 NOT NULL
        ) PRIMARY KEY (group_name, event_id)""",
        "CREATE INDEX ConsumerDeliveriesByConsumer ON ConsumerDeliveries "
        "(group_name, consumer, commit_ts, batch_index)",
        """CREATE TABLE ConsumerDeadLetters (
            group_name STRING(MAX) NOT NULL,
            event_id STRING(64) NOT NULL,
            dead_lettered_at TIMESTAMP NOT NULL,
            fields JSON NOT NULL
        ) PRIMARY KEY (group_name, event_id)""",
        # -- Graph projection (D4) -----------------------------------------
        f"""CREATE TABLE GraphNodes (
            label STRING(64) NOT NULL,
            node_id STRING(MAX) NOT NULL,
            props JSON NOT NULL,
            session_id STRING(MAX) AS (JSON_VALUE(props, '$.session_id')) STORED,
            embedding ARRAY<FLOAT64>(vector_length=>{embedding_dimensions})
        ) PRIMARY KEY (label, node_id)""",
        "CREATE INDEX GraphNodesBySession ON GraphNodes (label, session_id) STORING (props)",
        "CREATE VECTOR INDEX GraphNodesByEmbedding ON GraphNodes (embedding) "
        "WHERE embedding IS NOT NULL OPTIONS (distance_type = 'COSINE')",
        """CREATE TABLE GraphEdges (
            src_label STRING(64) NOT NULL,
            src_id STRING(MAX) NOT NULL,
            edge_type STRING(64) NOT NULL,
            dst_label STRING(64) NOT NULL,
            dst_id STRING(MAX) NOT NULL,
            props JSON NOT NULL
        ) PRIMARY KEY (src_label, src_id, edge_type, dst_label, dst_id)""",
        "CREATE INDEX GraphEdgesByTarget ON GraphEdges (dst_label, dst_id, edge_type) "
        "STORING (props)",
        "CREATE INDEX GraphEdgesByType ON GraphEdges (edge_type) STORING (props)",
        """CREATE PROPERTY GRAPH EngramGraph
            NODE TABLES (
                GraphNodes KEY (label, node_id)
                    DYNAMIC LABEL (label) DYNAMIC PROPERTIES (props)
            )
            EDGE TABLES (
                GraphEdges KEY (src_label, src_id, edge_type, dst_label, dst_id)
                    SOURCE KEY (src_label, src_id) REFERENCES GraphNodes (label, node_id)
                    DESTINATION KEY (dst_label, dst_id) REFERENCES GraphNodes (label, node_id)
                    DYNAMIC LABEL (edge_type) DYNAMIC PROPERTIES (props)
            )""",
    ]


def open_database(settings: SpannerSettings) -> Any:
    """Return a ``google.cloud.spanner`` Database handle for the settings.

    With ``create_if_missing`` the instance (emulator only) and the
    database with the full schema are created when absent.
    """
    if settings.emulator_host:
        os.environ["SPANNER_EMULATOR_HOST"] = settings.emulator_host
    from google.cloud import spanner

    client = spanner.Client(project=settings.project)
    instance = client.instance(settings.instance)
    if settings.create_if_missing and settings.emulator_host and not instance.exists():
        _create_emulator_instance(client, settings)
    database = instance.database(
        settings.database,
        ddl_statements=schema_statements(settings.embedding_dimensions),
    )
    if settings.create_if_missing and not database.exists():
        database.create().result(timeout=300)
        log.info("spanner_database_created", database=settings.database)
    return database


def _create_emulator_instance(client: Any, settings: SpannerSettings) -> None:
    from google.cloud.spanner_admin_instance_v1.types import Instance

    parent = f"projects/{settings.project}"
    operation = client.instance_admin_api.create_instance(
        parent=parent,
        instance_id=settings.instance,
        instance=Instance(
            name=f"{parent}/instances/{settings.instance}",
            config=f"{parent}/instanceConfigs/emulator-config",
            display_name=settings.instance,
            node_count=1,
        ),
    )
    operation.result(timeout=120)
    log.info("spanner_emulator_instance_created", instance=settings.instance)
