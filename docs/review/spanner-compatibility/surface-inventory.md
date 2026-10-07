# Source inventory → compatibility scenarios

Baseline: 6a30dcfd376d21b2732ffc36b8ed8847abb2a9de. Generated from AST, including multiline route decorators. Every cloud result must name its scenario IDs. Inherited graph methods are included through port contracts.

## API route functions

| Source | Route decorator | Function | Scenario family |
|---|---|---|---|
| `src/context_graph/api/routes/admin.py` | `router.post('/reconsolidate')` (router prefix applies) | `reconsolidate` | LIFE-01, LIFE-02, LIFE-03, LIFE-04, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, CONS-01, CONS-02 |
| `src/context_graph/api/routes/admin.py` | `router.get('/stats')` (router prefix applies) | `stats` | LIFE-01, LIFE-02, LIFE-03, LIFE-04, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, CONS-01, CONS-02 |
| `src/context_graph/api/routes/admin.py` | `router.post('/prune')` (router prefix applies) | `prune` | LIFE-01, LIFE-02, LIFE-03, LIFE-04, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, CONS-01, CONS-02 |
| `src/context_graph/api/routes/admin.py` | `router.post('/replay')` (router prefix applies) | `replay` | LIFE-01, LIFE-02, LIFE-03, LIFE-04, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, CONS-01, CONS-02 |
| `src/context_graph/api/routes/admin.py` | `router.get('/health/detailed')` (router prefix applies) | `health_detailed` | LIFE-01, LIFE-02, LIFE-03, LIFE-04, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, CONS-01, CONS-02 |
| `src/context_graph/api/routes/artifacts.py` | `router.post('/query/artifacts')` (router prefix applies) | `query_artifacts` | ART-01, ART-02, ART-03, ART-04, ART-05 |
| `src/context_graph/api/routes/context.py` | `router.get('/context/{session_id}')` (router prefix applies) | `get_session_context` | MEM-01, MEM-02, MEM-03, MEM-04, MEM-05 |
| `src/context_graph/api/routes/entities.py` | `router.get('/entities/{entity_id}')` (router prefix applies) | `get_entity` | USER-01, USER-02 |
| `src/context_graph/api/routes/events.py` | `router.post('/events')` (router prefix applies) | `ingest_event` | ING-01, ING-02, ING-03, ING-04, ING-05 |
| `src/context_graph/api/routes/events.py` | `router.post('/events/batch')` (router prefix applies) | `ingest_event_batch` | ING-01, ING-02, ING-03, ING-04, ING-05 |
| `src/context_graph/api/routes/events.py` | `import_router.post('/events/import')` (router prefix applies) | `import_events` | ING-01, ING-02, ING-03, ING-04, ING-05 |
| `src/context_graph/api/routes/feedback.py` | `router.post('')` (router prefix applies) | `submit_feedback` | FB-01, FB-02 |
| `src/context_graph/api/routes/health.py` | `router.get('/health')` (router prefix applies) | `health_check` | OPS-01, OPS-02, OPS-03, OPS-04, OPS-05 |
| `src/context_graph/api/routes/lineage.py` | `router.get('/nodes/{node_id}/lineage')` (router prefix applies) | `get_lineage` | MEM-01, MEM-02, MEM-03, MEM-04, MEM-05 |
| `src/context_graph/api/routes/ontology.py` | `router.get('/ontology')` (router prefix applies) | `get_ontology` | ONT-01, ONT-02, ONT-03, ONT-04 |
| `src/context_graph/api/routes/query.py` | `router.post('/query/subgraph')` (router prefix applies) | `query_subgraph` | MEM-01, MEM-02, MEM-03, MEM-04, MEM-05 |
| `src/context_graph/api/routes/simulate.py` | `router.post('/turn')` (router prefix applies) | `simulate_turn` | EXCLUDED: stateless LLM endpoint; optional output-to-ingestion app journey |
| `src/context_graph/api/routes/users.py` | `router.get('/{user_id}/profile')` (router prefix applies) | `get_user_profile` | USER-01, USER-02 |
| `src/context_graph/api/routes/users.py` | `router.get('/{user_id}/preferences')` (router prefix applies) | `get_user_preferences` | USER-01, USER-02 |
| `src/context_graph/api/routes/users.py` | `router.get('/{user_id}/skills')` (router prefix applies) | `get_user_skills` | USER-01, USER-02 |
| `src/context_graph/api/routes/users.py` | `router.get('/{user_id}/patterns')` (router prefix applies) | `get_user_patterns` | USER-01, USER-02 |
| `src/context_graph/api/routes/users.py` | `router.get('/{user_id}/interests')` (router prefix applies) | `get_user_interests` | USER-01, USER-02 |
| `src/context_graph/api/routes/users.py` | `router.get('/{user_id}/data-export')` (router prefix applies) | `export_user_data` | USER-01, USER-02 |
| `src/context_graph/api/routes/users.py` | `router.delete('/{user_id}')` (router prefix applies) | `delete_user` | USER-01, USER-02 |
| `src/context_graph/api/routes/webhooks.py` | `router.post('/webhooks/{source}')` (router prefix applies) | `receive_webhook` | HOOK-01, HOOK-02, HOOK-03 |

## Public storage contracts

| Port | Public method | Required family |
|---|---|---|
| `src/context_graph/ports/event_store.py:EventStore` | `append` | ING-01, ING-04 |
| `src/context_graph/ports/event_store.py:EventStore` | `append_batch` | ING-02, ING-04 |
| `src/context_graph/ports/event_store.py:EventStore` | `append_batch_outcomes` | ING-02, ING-05, OPS-04 |
| `src/context_graph/ports/event_store.py:EventStore` | `get_by_id` | LED-01, LED-02 |
| `src/context_graph/ports/event_store.py:EventStore` | `get_by_session` | LED-02 |
| `src/context_graph/ports/event_store.py:EventStore` | `search` | LED-02, SEARCH-01 |
| `src/context_graph/ports/event_store.py:EventStore` | `search_bm25` | SEARCH-01 |
| `src/context_graph/ports/event_store.py:EventStore` | `close` | BOOT-01 |
| `src/context_graph/ports/event_store.py:EventStoreAdmin` | `health_ping` | OPS-01 |
| `src/context_graph/ports/event_store.py:EventStoreAdmin` | `stream_length` | OPS-01, LED-02 |
| `src/context_graph/ports/event_log.py:EventLog` | `read_after` | LED-02, ONT-03 |
| `src/context_graph/ports/event_log.py:EventLog` | `get_documents` | LED-01, LED-02 |
| `src/context_graph/ports/event_log.py:EventLog` | `read_session_ids` | LED-02 |
| `src/context_graph/ports/event_log.py:EventLog` | `previous_in_session` | LED-02, PROJ-01 |
| `src/context_graph/ports/event_log.py:EventLog` | `trim` | LIFE-01 |
| `src/context_graph/ports/event_log.py:EventLog` | `expire` | LIFE-01, LIFE-02 |
| `src/context_graph/ports/event_log.py:EventLog` | `housekeep` | LIFE-01 |
| `src/context_graph/ports/event_log.py:MigrationTarget` | `append_imported` | EXCLUDED: cross-backend migration explicitly outside user scope |
| `src/context_graph/ports/event_log.py:MigrationTarget` | `last_legacy_position` | EXCLUDED: cross-backend migration explicitly outside user scope |
| `src/context_graph/ports/event_log.py:MigrationTarget` | `has_native_events` | EXCLUDED: cross-backend migration explicitly outside user scope |
| `src/context_graph/ports/subscription.py:Subscription` | `group_name` | SUB-01 |
| `src/context_graph/ports/subscription.py:Subscription` | `consumer_name` | SUB-01 |
| `src/context_graph/ports/subscription.py:Subscription` | `source_name` | BOOT-01 |
| `src/context_graph/ports/subscription.py:Subscription` | `ensure_group` | SUB-01 |
| `src/context_graph/ports/subscription.py:Subscription` | `claim_orphaned` | SUB-03 |
| `src/context_graph/ports/subscription.py:Subscription` | `delivery_counts` | SUB-01, SUB-02 |
| `src/context_graph/ports/subscription.py:Subscription` | `read_pending` | SUB-02, SUB-03 |
| `src/context_graph/ports/subscription.py:Subscription` | `read_new` | SUB-01, SUB-04 |
| `src/context_graph/ports/subscription.py:Subscription` | `ack` | SUB-02, SUB-03 |
| `src/context_graph/ports/subscription.py:Subscription` | `dead_letter` | SUB-02 |
| `src/context_graph/ports/subscription.py:Subscription` | `lag` | SUB-01 |
| `src/context_graph/ports/graph_reads.py:GraphReads` | `seed_events` | MEM-03 |
| `src/context_graph/ports/graph_reads.py:GraphReads` | `get_event_nodes` | MEM-01, MEM-03 |
| `src/context_graph/ports/graph_reads.py:GraphReads` | `cross_session_entity_events` | MEM-04 |
| `src/context_graph/ports/graph_reads.py:GraphReads` | `event_neighbors` | MEM-03, MEM-05 |
| `src/context_graph/ports/graph_reads.py:GraphReads` | `session_events_page` | MEM-01, MEM-05 |
| `src/context_graph/ports/graph_reads.py:GraphReads` | `session_edges` | MEM-01 |
| `src/context_graph/ports/graph_reads.py:GraphReads` | `lineage_chains` | MEM-02 |
| `src/context_graph/ports/graph_reads.py:GraphReads` | `record_access` | MEM-01, MEM-05 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `ensure_pack_schema` | BOOT-03, ONT-02 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `upsert_nodes` | PROJ-02, OPS-04 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `upsert_edges` | PROJ-03, PEXT-02 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `change_states` | PROJ-04 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `get_nodes` | PROJ-02, LED-01 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `find_nodes` | PROJ-03, ART-01 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `find_nodes_matching` | PROJ-03 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `find_latest` | PROJ-03 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `search_nodes` | ART-01, PEXT-02 |
| `src/context_graph/ports/pack_graph.py:PackGraph` | `neighbors` | ART-03, ART-04 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `merge_event_node` | PROJ-01 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `merge_event_nodes_batch` | PROJ-01, OPS-04 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `merge_entity_node` | EXT-01 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `merge_summary_node` | CONS-01 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `create_edge` | PROJ-01, EXT-01 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `create_edges_batch` | PROJ-01, OPS-04 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `get_subgraph` | MEM-03, MEM-04 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `get_lineage` | MEM-02 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `get_context` | MEM-01 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `get_entity` | USER-01 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `update_event_enrichment` | ENR-01 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `store_event_embedding` | ENR-01, ENR-02 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `merge_entity_node_raw` | EXT-01, EXT-02 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `merge_typed_edge` | EXT-01, EXT-02 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `get_entities` | EXT-01 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `search_similar_entities` | SEARCH-02, EXT-01 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `consolidate_entity_cluster` | CONS-02 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `adjust_node_importance` | FB-01, FB-02 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `ensure_constraints` | BOOT-03, LIFE-04 |
| `src/context_graph/ports/graph_store.py:GraphStore` | `close` | BOOT-01 |
| `src/context_graph/ports/user_store.py:UserStore` | `get_user_profile` | USER-01 |
| `src/context_graph/ports/user_store.py:UserStore` | `get_user_preferences` | USER-01 |
| `src/context_graph/ports/user_store.py:UserStore` | `get_user_skills` | USER-01 |
| `src/context_graph/ports/user_store.py:UserStore` | `get_user_patterns` | USER-01 |
| `src/context_graph/ports/user_store.py:UserStore` | `get_user_interests` | USER-01 |
| `src/context_graph/ports/user_store.py:UserStore` | `delete_user_data` | USER-02 |
| `src/context_graph/ports/user_store.py:UserStore` | `export_user_data` | USER-01 |
| `src/context_graph/ports/user_store.py:UserStore` | `write_user_profile` | EXT-02 |
| `src/context_graph/ports/user_store.py:UserStore` | `write_preference_with_edges` | EXT-02 |
| `src/context_graph/ports/user_store.py:UserStore` | `write_skill_with_edges` | EXT-02 |
| `src/context_graph/ports/user_store.py:UserStore` | `write_interest_edge` | EXT-02 |
| `src/context_graph/ports/user_store.py:UserStore` | `write_derived_from_edge` | EXT-02 |
| `src/context_graph/ports/user_store.py:UserStore` | `set_preference_superseded` | EXT-02 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `get_session_event_counts` | CONS-01 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `get_graph_stats` | OPS-01 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `write_summary_with_edges` | CONS-01 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `delete_edges_by_type_and_age` | LIFE-03 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `delete_cold_events` | LIFE-03 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `delete_archive_events` | LIFE-03 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `get_archive_event_ids` | LIFE-03 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `delete_orphan_nodes` | LIFE-03, USER-02 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `update_importance_from_centrality` | CONS-02 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `run_session_query` | CONS-01 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `session_agent_id` | CONS-01 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `session_events` | CONS-01 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `session_event_timeline` | CONS-01 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `events_for_pruning` | LIFE-03 |
| `src/context_graph/ports/maintenance.py:GraphMaintenance` | `delete_all` | LIFE-04/ONT-03: dedicated disposable databases only |
| `src/context_graph/ports/search.py:KeywordIndex` | `scores_are_native` | SEARCH-01, SEARCH-02 |
| `src/context_graph/ports/search.py:KeywordIndex` | `search` | LED-02, SEARCH-01 |
| `src/context_graph/ports/search.py:VectorIndex` | `scores_are_native` | SEARCH-01, SEARCH-02 |
| `src/context_graph/ports/search.py:VectorIndex` | `nearest` | SEARCH-02, MEM-03 |
| `src/context_graph/ports/health.py:HealthCheckable` | `health_ping` | OPS-01 |
| `src/context_graph/ports/archive.py:ArchiveStore` | `archive_events` | LIFE-02 |
| `src/context_graph/ports/archive.py:ArchiveStore` | `list_archives` | LIFE-02 |
| `src/context_graph/ports/archive.py:ArchiveStore` | `restore_archive` | LIFE-02 |
| `src/context_graph/ports/archive.py:ArchiveStore` | `close` | BOOT-01 |

## Composition roots and operations

- `api/app.py::lifespan` and `adapters/registry.py::open_stores`: BOOT/OPS; credential bootstrap cannot replace stores.
- `worker/__main__.py`: projection→PROJ/ONT, enrichment→ENR, extraction→EXT, pack_extraction→PEXT, consolidation→CONS/LIFE. Independent processes required for final acceptance.
- `ontology/__main__.py`: status/evaluate/rebuild→ONT, including recorded gates and same-backend rebuild catch-up.
- `migration/__main__.py`: excluded by fixed-backend requirement; no Redis/Neo4j runners.
- `scripts/engram_trial.py` and `scripts/spanner_probes.py`: diagnostics/reference only; observations and direct-adapter probes are not HTTP/worker E2E acceptance.
- `adapters/spanner/graph.py` inherits `GraphOperations` and `GraphOperationReads`: all port rows remain required even without an adapter override.
- Configuration-specific features: archive GCS vs FS, LLM/embedding providers, PPR/MMR/HyDE/intent/reranking, and multi-pack composition must be declared and mapped before execution.

Inventory closure requires method-level results or justified exclusion, not only family-level totals.
