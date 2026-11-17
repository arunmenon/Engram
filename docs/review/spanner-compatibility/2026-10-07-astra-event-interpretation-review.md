# Authoritative event interpretation review

Astra low reviewed receipt validation before bound ledger content is returned to workers, replay/session/search readers, enrichment and archive. Exact bundle and engine identity remain required; an epoch-only restart can interpret earlier accepted events. Changed-contract compatibility grants and graph-derived summary provenance are not implemented in this slice.

## Finding and disposition

P2: the pack extraction worker returned early when no profiles were enabled, acknowledging delivery without reading its authoritative receipt. Resolved: any delivery with an event ID fetches and validates its stored document before selecting extraction profiles. The actual consumer-loop regression includes an empty-profile worker and proves control refusal stops without ACK, DLQ, model prompt or graph plan.

Astra source recheck: P2 resolved, no remaining finding within this bounded recheck. Reviewer ran no tests or cloud operations.

## Verification

Run `20261007-local-event-interpretation-01`: 278 passed, one failed obsolete test expecting delivery hints to override stored event type; retained.
Run `20261007-local-event-interpretation-02`: 280 passed, two warnings; scoped typing passed. Ruff found an overlong test line.
Run `20261007-local-event-interpretation-03`: selected Ruff and whitespace checks passed after formatting-only correction.

Behavioral verification uses transaction fakes and actual consumer loops; this slice has not run on real Spanner yet. Baseline scenarios remain unchanged. Runtime changes and these records remain local and uncommitted; no issue is closed by this review.

## Follow-up boundaries found during cloud-harness preparation

The pending-drain retry-exhaustion branch in `BaseConsumer._drain_pending` checks delivery count and can dead-letter before calling `process_message`. Therefore current document-fetch guards do not yet prove authority validation before **every** terminal disposition. This requires a separate guarded-disposition design and exhausted-delivery cloud assertion; fresh-delivery and restored-pending checks must not be treated as covering it.

Full-worktree typing audit `20261007-local-full-typing-01` reports52errors in12files (153sourcefiles checked), a publication gate independent of this slice's scoped typing pass.
