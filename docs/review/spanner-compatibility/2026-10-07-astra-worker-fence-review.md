# Worker control-fence handling review

2026-10-07. Tight read-only review of neutral RuntimeFencedError, affected worker handlers, consolidation supervision and focused tests. No tests/cloud executed.

**Verdict: approve this bounded worker error-handling change; no blocking swallowing/cancellation regression identified.**

RuntimeFencedError is distinct from transient outage errors; the existing retry helper therefore propagates it immediately. Base pending/new/idle processing catches it ahead of ordinary event-error handling, stops and reraises before success accounting or subsequent acknowledgments. A refused ack propagates as a control failure rather than a successful delivery. Projection propagates fences from planning, batch apply and per-event fallback, avoiding dead-letter classification. Extraction session-ID reads no longer convert a fence refusal into an empty successful session. Consolidation guarded cycles stop/reraise instead of logging ordinary failure or success.

The consolidation runner supervises timer and base-consumer tasks using FIRST_COMPLETED. A fenced background timer is awaited and propagated, with both tasks canceled and joined in finally; an independently failed base loop also propagates and cancels the timer. Parent cancellation reaches finally and joins both owned tasks. Ordinary base completion retains timer cleanup. No unowned background task is introduced by this change.

Inspected `20261007-local-worker-fence-01/pytest.txt`: **144 passed**, 3.07 seconds. Focused tests cover pending/new/idle/ack refusal, no transient retry, projection planning/batch/fallback refusal, extraction read refusal, consolidation cycle behavior and cancellation/join of a blocked base loop after a background fence. Useful additional regression coverage would explicitly exercise base-loop failure and external cancellation of the two-task runner; code inspection supports those paths, but the new test specifically proves the timer-failure direction.

This establishes worker handling when a fence error is raised, not complete fence coverage or absence of prior committed effects. SDK thread-backed transactions already in progress cannot be undone merely by asyncio cancellation; transaction-local fence checks and replay/idempotence remain the governing contract. Production tenant startup remains disabled, with no cloud or end-to-end activation acceptance claimed.
