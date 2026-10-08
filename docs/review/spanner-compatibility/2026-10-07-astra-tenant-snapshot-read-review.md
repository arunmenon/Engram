# Tenant snapshot read review

2026-10-07 — Astra low, read-only inspection; no tests or cloud calls executed.

**Verdict: approve this bounded snapshot-read slice. No blocking findings.** Public tenant activation remains disabled. This review does not approve final-response fencing, retriever exception propagation, or complete production isolation.

- `tenant_control.py:203` verifies the physical database and reads ownership before yielding the same `snapshot(multi_use=True)` object for application reads. No staleness option is supplied. Control rows are materialized before yielding; all seven adapter paths also consume their application result iterators inside that context. There is no separate control-check snapshot followed by an unguarded application snapshot in these paths.
- The two graph paths, two ledger paths, and three subscription paths all use the shared helper. Constructor and helper validation restrict modes to `read` or `processing`; typos cannot silently acquire drain permission. Invalid database, identity, epoch, or serving state fails before application rows are requested.
- Registry forwards the selected mode to graph, ledger, and subscription creation. Bound worker factories explicitly choose `processing`; ordinary API/default adapter reads retain `read`. Thus existing workers may read while draining, while external reads require active ownership. Frozen or stale-epoch processing reads still fail. The registry's active-only startup ownership check remains intentionally stricter than continuing an already-open worker during drain.
- `subscription.py:lag` now rethrows `RuntimeFencedError` before its legacy best-effort metric exception handler. Unbound helpers retain the previous ordinary snapshot construction and do not read TenantControl.

Recorded evidence: `runs/20261007-local-tenant-read-snapshots-01/pytest.txt` reports **137 passed, 1 dependency deprecation warning**. The dedicated matrix exercises all seven paths, active/draining processing permission, external drain/frozen/stale refusal, and zero application accesses following control refusal. Its fake requires multi-use snapshots and records ordering; the actual same-context guarantee is additionally established by source inspection.

Nonblocking coverage refinement: add a small parameterized constructor/helper invalid-mode test and an explicit unbound snapshot-options test. The source validation and compatibility branches are straightforward; these are regression-strengthening suggestions, not required changes.

A successful read is authorized at its snapshot timestamp only. A later owner transition can occur before an assembled response is released; the explicitly deferred response checks and broad-catch audit remain necessary before a production isolation claim.

## Propagation and drain-restart addendum

Reviewed against `2026-10-07-astra-read-fencing-design-review.md`. **Source changes approved in bounded scope; test-evidence correction required before marking this addendum verified.**

Registry startup now checks the explicitly selected operation. This supersedes the earlier active-only startup observation: bound processing workers may reopen during draining while preserving exact owner/epoch/digest validation; ordinary API startup remains active-only. All five factory forwarding assertions now require processing mode.

Vector/BM25 fallbacks rethrow `RuntimeFencedError`; gathered channel results are scanned for the refusal before fusion, preventing another successful channel from hiding it. Graph/ledger health, EvalPending refresh fallback, admin stats/health, import append reporting, replay catch-and-continue, and rebuild batch/per-event fallback likewise rethrow the control error before ordinary degradation. Existing non-control fallback behavior is retained. Ledger partial-batch and archive fallback guards also preserve the refusal.

**P2 — new retrieval regressions do not execute:** `tests/unit/test_spanner_tenant_reads.py:100` and `:121` import `test_retrieval_engine` as a top-level module. Recorded `20261007-local-tenant-read-snapshots-02/pytest.txt` reports **3 failed, 230 passed, 43 warnings**, with all three failures being `ModuleNotFoundError` at these imports. Use `tests.unit.test_retrieval_engine` and retain a registered rerun. No runtime flaw was identified in this addendum.

The EvalPending test forces refresh with zero TTL; it does not prove cache-hit authorization. Final external response guards, cached/empty-return authorization, cursor binding and streaming controls remain deferred. Public tenant startup is still disabled. Reviewer ran no tests or cloud calls.

### Propagation evidence recheck

The import P2 is **resolved**: both imports now use `tests.unit.test_retrieval_engine`. Retained run02 remains failed; `20261007-local-tenant-read-snapshots-03/pytest.txt` reports **233 passed, 43 dependency warnings**. Approve the bounded propagation/drain-restart addendum with this corrected local evidence. No reviewer tests/cloud calls; the previously listed external response/cache/cursor/streaming gates remain pending.
