# Runbook: bulk importing event history

How to load a large history of events into Engram: a year of a tool's activity, a backfill for a new ontology pack, or events exported from another system. To move an existing Engram ledger between storage backends, use `docs/runbooks/storage-migration.md` instead.

## Which endpoint

| Endpoint | For | Limits | Trust |
|---|---|---|---|
| `POST /v1/events` | one event from an agent | `CG_INGEST_MAX_BODY_BYTES` (10 MB) | the agent id must not start with `webhook:` |
| `POST /v1/events/batch` | agents sending small batches | `CG_INGEST_BATCH_MAX_EVENTS` (1,000) per request, 10 MB | as above |
| `POST /v1/events/import` | history: thousands to hundreds of thousands of events | `CG_INGEST_IMPORT_MAX_EVENTS` (500,000) and `CG_INGEST_IMPORT_MAX_BODY_BYTES` (200 MB) per request | admin key; `webhook:` ids allowed |

All three accept `Content-Encoding: gzip`. The size limits apply both to the bytes sent and to the bytes after decompression. A body not received within `CG_INGEST_BODY_READ_TIMEOUT_S` (60 s) gets 408.

## The import endpoint

```
gzip -c history.ndjson | curl -sS -X POST "$ENGRAM/v1/events/import" \
  -H "Authorization: Bearer $CG_AUTH_ADMIN_KEY" \
  -H "Content-Type: application/x-ndjson" -H "Content-Encoding: gzip" \
  --data-binary @- > outcomes.ndjson
```

**Input.** One event per line, in the same shape as `POST /v1/events` (`event_id`, `event_type`, `occurred_at`, `session_id`, `agent_id`, `trace_id`, `payload_ref`, optional `payload`). Blank lines are skipped. Every line is validated like a batch item, and the event types must be declared by the active ontology packs.

**Trust.** The import runs behind the admin key. When `CG_AUTH_ADMIN_KEY` is configured, the caller has proved it, so events may carry the `webhook:` agent ids that only the signed webhook routes may otherwise use. Imported tool history is then marked trusted, like live webhook events: trust comes from the credential, not from the agent id. With no admin key configured (development), those ids are refused. Any other agent id is trusted if it is listed in `CG_ONTOLOGY_TRUSTED_SOURCES`.

**Output.** A stream of NDJSON lines, one per input event:

- `rejected`: invalid, with `errors` (`field`, `message`). These come first, in input order.
- `created`: written, with `global_position`.
- `duplicate`: its `event_id` was already in the ledger, with the stored `global_position`. The position is `null` if the stored document has expired.
- `failed`: not written, with `error`.

Each line carries `index`, the event's position among the non-blank input lines, and `event_id`. The last line is `{"summary": {"received", "order", "created", "duplicate", "rejected", "failed"}}`.

**Writes.** Events are appended `CG_INGEST_IMPORT_BATCH_SIZE` (500) at a time.
- On Redis each event is written atomically on its own, so one failed write is `failed` without affecting the others.
- On Spanner each chunk is one transaction, written whole or not at all.
- If the store fails, every remaining event is `failed` and the import stops.

**Resuming.** Imports are idempotent by `event_id`: send the same file again. Events already written come back `duplicate`, and the rest are written.

## Ordering contract

- **Within an import.** With `?order=occurred_at` (the default), the valid events are appended in occurrence order, ties in input order. With `?order=input`, they keep the file's order.
- **Against the ledger.** Imported events land after everything already in the ledger. `global_position` is arrival order, and the live ledger is never reordered.
- **What depends on order.** The projection worker draws `FOLLOWS` between a session's events in log order. Pack rules see events in log order too (`to_latest` lookups, `only_from` transitions).

So:

1. Import a session's history **before** its live events start arriving, or accept that the history follows them in the log.
2. Send **one import at a time per session**. Two concurrent requests for the same session interleave.
3. For pack rules that look across sessions (a deployment and the incident on it), import related history in one request, so occurrence order holds across sessions. `to_latest` lookups also never look past an event's own time, so a deployment imported later is never linked to an earlier incident.

## Deduplication window

Duplicates are recognised while the ledger remembers the `event_id`:

- **Redis:** until the dedup set entry is pruned, after the retention window.
- **Memory and Spanner:** while the event row exists.

Re-importing history older than the retention window writes it again.

## Rate limits

- **Requests:** every request counts once against `CG_RATELIMIT_STANDARD_RPM`.
- **Events:** `/v1/events` and `/v1/events/batch` also draw on a per-client event quota, `CG_INGEST_EVENTS_PER_MINUTE` (60,000; 0 turns it off). A 1,000-event batch costs 1,000 events. An exhausted quota answers 429 with `Retry-After`.
- **Imports:** the import endpoint, which needs the admin key, does not draw on the event quota.
- **Scope:** both limiters are kept in each API process, not shared between replicas.

## After the import

The projection worker reads the imported events like any others: watch its lag (`CONSUMER_LAG`) until it reaches zero. It reads and writes a flush of `CG_CONSUMER_PROJECTION_BATCH_SIZE` events (50) at a time, in a few calls per flush. For a large backfill, a larger flush (200 to 500) means fewer round trips, at the cost of more events retried together if a flush fails. For a new ontology pack, run its evaluation set once the history is projected:

```
python -m context_graph.ontology evaluate --record
```

Its intents are used from then on (`docs/runbooks/pack-authoring.md`, step 4).
