# Writer admission integration review

2026-10-07 — Astra low, source and recorded-evidence inspection only. No tests/cloud calls executed.

**Verdict: one P1 binding-integrity correction required.**

## P1: independently supplied bundle is not verified against ledger authority

`src/context_graph/adapters/spanner/log.py:247` compiles any supplied `tenant_bundle`; neither construction nor `_acceptance` ties that bundle to the fence's interpretation digest. A direct caller can construct a ledger with a valid core-only fence/engine/context but a PDLC-enabled bundle. New PDLC events then pass that policy and are stamped with the core-only authority's acceptance digest. Current-control fencing still succeeds, so the receipt falsely attributes admission to the pinned configuration.

Registry supplies the correct combination, but direct bound append methods are explicitly part of this slice's boundary. Require a trusted binding/configuration association at construction and validate bundle, fence and engine together before allowing writes. For example, consume the binding's validated pinned bundle and verify its fence identity, rather than accepting independently assembled authority/policy inputs. Add a mismatched-bundle regression proving refusal before a transaction. The existing policy-replacement test is useful for duplicate ordering but does not establish constructor pinning.

## Other reviewed behavior

New-row policy checks occur after stored/same-chunk duplicate and conflict decisions, inside the fenced transaction callback. Rejected rows do not enter insertion mutations; valid siblings retain indexed partial-success outcomes. All normal direct and request-proxy append variants reach the shared path. Events and payloads are deep-copied before thread handoff, and fingerprinting/persistence retain the original observationally validated payload. Payload-list length mismatches now fail explicitly.

Single and batch API paths defer bound pack decisions to storage, preserving historical duplicate ordering; contract rejection maps to 422, identity conflict to 409, and storage failure to 503 when no sibling succeeds. Batch diagnostics retain original input indexes, event type and sanitized reason/path data. Bound imported/bare-entry refusals remain; unbound generic admission policy remains unchanged apart from explicit length validation.

Inspected run `20261007-local-writer-admission-02`: **214 passed, 3 framework warnings**; recorded selected Ruff and scoped mypy checks passed. This is transaction-fake/HTTP evidence, not cloud acceptance. Source-trust enforcement, bound imports/webhooks and full all-source admission remain explicitly deferred.

## Binding-integrity recheck

**P1 resolved in source.** The constructor now accepts `tenant_binding`, reconstructs its digest, compares the complete derived fence and engine revision, and compiles only that binding's pinned bundle. Registry forwards the binding. Missing binding still permits read-only bound ledger construction, while authenticated writer creation and append fail closed.

The existing acceptance cloud case passes the same binding to its normal and chunked ledgers and the renewed binding to its renewed ledger. These call-site changes preserve the reviewed core-only fixture scope; no new cloud behavior was executed or approved as evidence.

**P2 test-evidence correction:** recorded `20261007-local-writer-admission-04/pytest.txt` has **1 failed, 219 passed, 3 warnings**. At `tests/unit/test_spanner_pack_admission.py:244`, the nested-mutation case changes `binding.bundle.registry`, which deliberately returns an independent reconstructed view. The pinned bundle does not change, so expecting constructor refusal is incorrect. Replace this case with an isolation assertion: modifying that view leaves construction valid and core-only admission unchanged. Retain genuine bundle/engine/tenant/epoch/missing-fence rejection cases. Source approval is bounded; mark verification complete only after a registered successful correction run. No tests/cloud executed by reviewer.

## Detached-view correction and bounded cloud-case extension

The test-evidence P2 is corrected in source: the detached-registry case now asserts successful construction, unchanged refusal of `tool.custom`, and no transaction. Run05 was still in progress when inspected; no passing total is assumed.

The acceptance harness now attempts unknown `tool.custom` and inactive `pdlc.change.created` using its existing two owned IDs, checks rejected status/reason/no position, and compares all application-table fingerprints before valid writes. Direct and authenticated-proxy append paths must raise InvalidRequestError, followed by another unchanged fingerprint. Later existing valid creation/concurrency assertions reuse those IDs, establishing that rejection reserved neither identity. Durable original fixture intent, settlement, ownership and cleanup remain unchanged; no extra IDs or effects are authorized.

**Approve the corrected writer slice and this bounded core-only cloud admission regression, subject to its registered preflight result.** No remaining source blocker identified. This extension proves inactive-domain refusal, not active PDLC cloud acceptance. Reviewer executed no tests/cloud calls; existing full source-trust and multi-source limitations remain.

## Final bounded evidence disposition

Inspected local run05 output: **235 passed, 3 framework warnings**, selected Ruff clean, and scoped mypy clean for three source files. The detached-view test correction is verified; prior failed runs remain retained.

Inspected `20261007-cloud-writer-admission-01/{observations,case-attempt,results}.json`: all **23 checks passed**, including unknown-core/inactive-domain refusal with no application writes, direct/proxy enforcement, subsequent valid reuse of the two IDs, duplicate/conflict/concurrent-writer and receipt-preservation regressions, exact fixture removal, unchanged schema/application-table fingerprints, and unchanged source. The durable case record identifies exactly two cleanup IDs and retains the same owner active at epoch 6 after the planned epoch-5 freeze/recovery. The generic results label “schema checks” is broader in its underlying observations: the 23 include admission, retention, identity and cleanup checks.

**Final verdict: approved for the tested bounded writer-admission implementation and core-only cloud harness scope. Both review findings are resolved.** This is not full PDLC cloud acceptance, full-baseline promotion, source-trust enforcement, trusted import/webhook enablement, or general Spanner compatibility. Reviewer inspected retained evidence only and performed no reruns/cloud actions.
