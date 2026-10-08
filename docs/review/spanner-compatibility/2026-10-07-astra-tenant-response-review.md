# Private tenant response guard review

2026-10-07 — Astra low, read-only source/evidence review; no tests or cloud calls executed.

**Verdict: one P2 correction requested for bounded buffering.** No authorization leak identified in the reviewed ordinary-response path. Public tenant activation remains disabled.

## Finding

**P2 — chunk bookkeeping is unbounded despite the payload limit.** `src/context_graph/api/tenant_responses.py:93` appends every chunk to a list, including empty `more_body=True` chunks. Empty chunks consume no byte budget; arbitrarily many can grow the retained list indefinitely. Tiny chunks likewise incur substantial per-chunk overhead beyond the advertised 8 MiB payload bound. Accumulate into one bytearray under the existing byte limit, or additionally enforce a strict chunk count. Add an empty-chunk regression and retain the existing oversized-payload refusal test. This is a small correction to the stated bounded-materialization contract, not a request for a general streaming subsystem.

## Reviewed behavior

The guard validates a same-tenant trusted Principal before storage. Private import and cursor requests are refused before handlers. Registry supplies an uncached strict-active ownership check using a fresh snapshot for each invocation, even when its stores have processing read mode. The guard checks before execution and again after terminal body receipt, covering ordinary empty and cached responses.

Response start, headers and body remain withheld until final authorization. Fence/check failures produce a sanitized 503 without private response headers or data. Duplicate starts, missing starts, incomplete responses and unsupported ASGI messages fail closed before release. Cancellation is not converted into a successful response. Once release starts, send/background failures cannot retract bytes; the implementation correctly avoids attempting a replacement response. Arbitrary application exceptions remain ordinary framework errors rather than private buffered output.

Middleware installation is confined to the private bound factory; legacy unbound applications retain their existing behavior. Existing BaseHTTPMiddleware chunking is accommodated by waiting for its terminal body. This is bounded response materialization, not unrestricted streaming support. A nonterminating response can still occupy a request until cancellation; the body guard does not claim a request timeout.

Recorded `20261007-local-tenant-response-01/pytest.txt`: **101 passed, 2 dependency warnings**. Tests cover precheck refusal, final refusal with private headers/chunks, empty/cache responses, forbidden entry paths, payload overflow and actual private FastAPI middleware execution. No direct cancellation regression was included.

The fresh final check is the authorization linearization point; a subsequent epoch transition may overlap network delivery. Direct engine calls, durable cursor design, public activation and complete production isolation remain outside this approval.

## Correction recheck

The bounded-buffer P2 is **resolved**. A single bytearray now accumulates payload after enforcing the byte cap; empty chunks retain no per-chunk entries. Final bytes conversion adds bounded payload-copy overhead, not growth with chunk count. The new regression sends 1,000 empty chunks followed by a two-byte terminal payload at a two-byte cap and preserves both authorization checks.

The private child additionally registers a sanitized `RuntimeFencedError` 503 handler. The real FastAPI integration regression verifies an inner control refusal cannot become a generic 500 or disclose its detail while both outer checks pass.

Inspected retained `20261007-local-tenant-response-02/pytest.txt`: **103 passed, 2 dependency warnings**. **Approve the bounded private response slice; no remaining blocker identified.** No tests/cloud executed by reviewer. Previously stated final-check linearization and production-release limitations remain unchanged.
