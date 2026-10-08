# Database-scoped Entity ANN DDL recovery

2026-10-07. Narrow #44 design follow-up. Inspected local migration/harness code and the installed Python SDK under `/private/tmp/engram-ontology-review-venv`; consulted official API documentation. No code changes, tests, cloud calls or permission changes. The upgrade01 failure and IAM results from `20261007-cloud-entity-ann-iam-01` are supplied evidence, not independently rerun here.

## Decision

Replace operation listing with recovery of a **persisted, exact database operation name**. Do not expand instance permissions. The current list-based harness must not run again until both listing sites are removed: `upgrade_entity_index` preflight and the harness's post-apply evidence gathering.

The installed `Database.list_database_operations()` delegates to its instance with a database metadata filter; that filter does not change the parent authorization resource. `Database.update_ddl` accepts `operation_id`. The API defines identifiers as `[a-z][a-z0-9_]*`, constructs `<database>/operations/<operation_id>`, and returns ALREADY_EXISTS for a reused existing name. This provides a recovery identity, not automatic replay of the original result. [Official updateDdl contract](https://docs.cloud.google.com/spanner/docs/reference/rest/v1/projects.instances.databases/updateDdl).

## Minimal API and durable record

Keep the pure physical-schema planner. Replace the executor with a known-attempt contract, for example:

```python
upgrade_entity_index(database, dimensions, *, attempt, operations_client,
                     persist_attempt, timeout_s=60) -> UpgradeOutcome
```

`attempt` contains database resource, migration/version, dimensions, stable operation ID/full name, exact ordered statements, their digest, parent attempt for retries, and last observed state. `persist_attempt` must atomically save changes before submission. A persistence failure prevents submission. An outcome distinguishes no-op, pending/uncertain, terminal failure, and successful operation plus validated target readiness; an empty statement list alone is not success.

The harness allocates and registers the operation ID/full name **before any cloud calls**, alongside its existing target/source manifest. After read-only planning, it durably fills statements/digest before the update RPC. Reusing an ID with different target, dimensions or statements is rejected locally. Do not derive a fresh operation ID from each process/run restart. An explicit `--resume-attempt` restores the original record; a different evidence-run ID may refer to that same attempt.

Use the existing authenticated DatabaseAdmin transport's operations client, supplied by the harness, rather than creating a client with a different endpoint or credentials:

```python
raw = operations_client.get_operation(full_name, timeout=rpc_timeout)
future = google.api_core.operation.from_gapic(
    raw, operations_client, google.protobuf.empty_pb2.Empty,
    metadata_type=UpdateDatabaseDdlMetadata,
)
future.result(timeout=wait_timeout)
```

Installed SDK sources confirm `get_operation(name)` returns the raw long-running Operation, adds routing metadata for that exact name, and `update_database_ddl` wraps it with these same Empty/UpdateDatabaseDdlMetadata classes. Check returned name and metadata database/statements against the durable attempt before accepting/resuming. Missing or inconsistent metadata is unresolved, not permission to submit unrelated DDL. Preserve bounded polling and original operation errors.

## State transitions

1. **GET returns NotFound for an unsubmitted attempt:** reload/validate physical schema and plan. If already correct and READ_WRITE, record a no-op without submitting. Otherwise persist the ordered plan and invoke `database.update_ddl(plan, operation_id=attempt.id)`. Save submission intent before RPC, not merely its returned name afterward.
2. **Operation exists, pending:** observe/wait on that operation only. Do not replan a suffix or launch another ID because the column or index now appears. DDL is incremental; physical visibility does not prove completion. Timeout leaves the attempt pending, with its exact name available for recovery.
3. **Operation exists, terminal success:** reload and run the target handshake. Only success plus compatible READ_WRITE schema closes the attempt. A readiness/schema mismatch remains an explicit failure; do not automatically start repair DDL.
4. **Operation exists, terminal failure:** preserve error code/message, metadata and visible partial schema. A separately explicit retry allocates a new linked ID and plans only remaining compatible additions. Reusing the failed ID cannot retry its statements. No automatic new-ID fallback.
5. **Submission response lost or transport deadline/unavailability:** retain an uncertain state and GET the original name. ALREADY_EXISTS also means GET that name; it never means “ignore and accept schema.” If GET returns NotFound, only a bounded replay of the **identical persisted request with the same ID** is permitted; never replan or change ID. If the result remains unclear, stop unresolved. Previously observed operations that later disappear require explicit reconciliation; do not assume absence proves they never executed.
6. **GET denied/unauthenticated/unavailable:** distinguish this from NotFound; preserve the record and stop without submission or broader-permission requests. A terminal operation error is different from an RPC error while attempting to observe it.

A successful previous attempt plus unchanged schema makes a repeated apply an observed success/no-op, not another migration. A new explicit retry is allowed only after the predecessor is confirmed terminal. Local file locking avoids duplicate harness processes but does not prove no external DDL exists; this executor guarantees coordination of its registered attempts, not a global database-operation lock. Document that boundary without introducing instance listing.

## Harness and regression requirements

Always include registered operation name, request digest, last state, RPC/operation error distinction and predecessor ID in evidence, including failed applies. Write state before calls and in exception/finally paths; `on_operation` after submission is insufficient when the initial response is lost. Post-apply evidence uses exact GET only. Preserve existing source hashes and graph fingerprints; close resources normally after errors.

Focused fake-client tests must make all list methods fail if called. Cover registration/persistence failure before submission; new absent operation; lost submission response; same-ID ALREADY_EXISTS; pending operation with partially or fully visible target DDL; success with ready/not-ready schema; terminal failure with partial application; explicit linked retry; GET permission failure versus NotFound; digest/name/metadata mismatch; process restart restoring the attempt; and previously observed operation disappearance. Assert exactly which update calls occur and their stable IDs/identical statement payloads.

Before another authorized cloud apply, locally verify these transitions and register its attempt. Cloud acceptance then uses the existing database-scoped token to GET the known operation, submit/resume once, obtain terminal status and verify schema/readiness. No instance listing or IAM change is required by this design. This review does not establish successful DDL submission or cloud readiness.
