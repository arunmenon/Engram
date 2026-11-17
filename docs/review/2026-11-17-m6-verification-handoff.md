# M6 technical verification handoff

Status: **Fable independently accepted M6’s bounded technical scope; operator study pending**. M6-1 and M6-2 require pre-session disposition; see `docs/review/2026-11-17-m6-pre-session-disposition.md`. This is not a release or self-service readiness claim. It supersedes the remaining-work list in the first-pass report for the specifically closed rows; historical failures remain recorded.

## Reproducibility

Reviewer: Codex, implementer; not independent, uncoached or human-participant research. Branch/HEAD, dirty-tree limitations, engine identity, frontend bundle/source hashes and copy revisions are recorded in `output/playwright/ai-native-onboarding/M6/final-20261117/manifest.json`. Browser: headed Google Chrome through Python Playwright, 1440×1000 and selected 430×932 checks. Credentials were read inside automation, never printed.

Services: 8135 live agent/isolated memory (`m6-completion-implementer`), 8136 fixture agent/isolated memory (`m6-recovery`), 8137 real registered Spanner sandbox/no author (`m6-implementer`). These processes were reused from the earlier verification, not newly rebuilt services. A frontend rebuild produced the same `workbench-B3e2IkoC.js` bundle. Original snapshots remain untouched; test copies and their controlled changes are identified in the evidence.

Primary evidence: `output/playwright/ai-native-onboarding/M6/final-20261117/`. Earlier recovery evidence: `M6/completion-20261116/recovery/`. Initial multi-domain Spanner and incomplete live procurement evidence: `M6/baseline-20261116/`.

## Outcomes

| Objective | Result and boundary |
| --- | --- |
| PDLC duplicate/conflict discrepancy | Memory batch outcomes compare canonical request fingerprints. Identical retry is duplicate; changed request conflicts. Frozen story/expected outcomes unchanged. Three regression cases and 25 memory conformance cases passed in the prior continuation. Direct legacy append semantics and tenant authorization are not changed by this fix. |
| Current PDLC through Chrome/memory | 111 checks pass; same story, pack digest and engine as Spanner. `memory/pdlc-memory-result.json`, `preservation-proof.json`. |
| Current PDLC through Chrome/Spanner | 111 checks pass, epoch 33, cleanup verified, slot released and available. `pdlc-result.json`, `capacity-after-pdlc.json`. |
| Spanner failure disposition | Previous epoch-32 run failed on cleanup DeadlineExceeded; no completed result was published. Later read-only status was ready without manual release. Fresh run passed in 78.4 seconds. This establishes non-reproduction and recovery, not a proven root cause or a code fix for the transient failure. No timeout increase, schema change or ownership reset. |
| Live non-PDLC complete control | Retained CRM baseline → live explanation HTTP 200 → operator request → live author revision → review → sandbox → approval for handoff. Contact identity becomes permanent CRM ID. F1 1.0 shows no regression on two existing questions; neither tests Ann’s email change. One contact for Ann is observed in the recorded graph. No activation. |
| Preservation in live revision | Sources and question oracles unchanged. Parsed deal lifecycle, deal projection rules and retrieval settings equal the baseline. Explicit `direction: both` merely spells out the parser default. `preservation-proof.json`. |
| Expectations | Acme graph-existence assertion was recorded from the source event before execution. Existing question expectations were not changed. Expectations/acknowledgements are implementer-reviewed synthetic material, not independently reviewed domain truth. |
| Live incomplete control | Prior neutral procurement request returned no executable pack and asked about missing supplier linkage, conflicting reopening policy and unit identity. Retain its provider metadata and limits; one run is not proof of general detection. |
| Fresh intake | New procurement draft and three pasted materials through UI; repeated 42 exposes east/west, texts/categories survive reload, no author/explain call. `intake-result.json`. File chooser/PDF handling not tested in this pass. |
| No lifecycle / no relationship | Directory fixture has no lifecycle confirmation. Separate relationship-free question uses the actual initial-authoring clarification helper; UI asks for relationship evidence or explicit deferral, and Run remains disabled. This helper fixture is not a live-agent result. |
| Wrong/unsupported answers | Frozen incident-operations story returns 4 passed, 2 failed, 1 unsupported. Expected/recorded differences are readable outside technical JSON. Scalar question is not a pass. Fixture read-only explanation and rerun preserve the wrong expectations and failure. `failure-rerun.json`. |
| Recovery | Current Chrome checks retain request/answer after failure/retry and reload; one named Keep-data editor; ticks survive navigation/reload. See continuation recovery scripts/screenshots. |
| Source edit during explanation | Concurrent API-assisted source edit during UI explanation; no old claim displayed. Browser response wait timed out, so do not claim that response was observed as 409. A subsequent stale API request returned 409. This is mixed UI/API evidence, not a fully observed late-response browser trace. |
| Checks | 571 selected backend/architecture tests; 19 frontend tests; frontend build; Ruff; mypy 25 source files pass. See exact commands/scripts and output. This is not a claim that the entire repository suite ran. |

## Product changes versus verification

The preceding continuation changed memory batch outcome identity checks and clarified explanation scope in the live-agent prompt; the server's grounding/permission checks were not relaxed. This final pass made no further product changes. Snapshot setup, browser harnesses, reports and the review handoff are verification artifacts.

The first explanation rejected structured decision options returned for a limitation. After explicit scope instructions, live explanation passed. A successful explanation does not guarantee correct business advice: the generated explanation/request can still contain technical names. The operator's submitted answer in the final chain contains no engine identifiers; generated instructions and actual response are saved separately.

## Remaining findings and acceptance boundaries

- **Independent technical review accepted:** `docs/review/2026-11-17-m6-fable-independent-review.md` accepts the bounded scope and closes M5-1/2. The new M6-1 UI remedy still needs a focused independent recheck before human sessions.
- **Human comprehension pending:** no real operator session has been run. Domain-persona simulations and browser automation do not substitute for it.
- **Graph confirmation friction:** selecting graph outcomes and ticking review in the same save resets that tick. The final script returns to the saved selection and confirms it explicitly; no gate is bypassed. Fable should judge the task impact and smallest remedy before a human session.
- Historical technical-vocabulary findings, M2b/M3/M4/M5 lows and broader self-service claims remain as previously recorded. The successful CRM case does not close every legacy proposal issue.
- The source-race browser trace remains partial as described above. Full keyboard, screen-reader, simultaneous tenants, process-interruption cleanup and all recovery-matrix permutations were not newly exercised here. Preserve their prior evidence or mark unverified; do not infer blanket accessibility/reliability.
- No production deployment, new database, source expectation rewrite or runtime activation. Approved means a saved handoff artifact only.

## Real-operator session, after the Fable gate

Use 3–5 unfamiliar operators, rotating procurement, CRM and incident operations. Ask each to identify record identity and its source, ask a read-only question, review a proposed consequence, reject a wrong answer/weak check, recover from a failed request, recognize an unsupported question, and distinguish tested/approved/active. Record actual actions, help requests, incorrect approvals and lost input; no coaching during a task. Stop for any critical wrong approval. Keep a reviewer field for expected answers; otherwise label them author-reviewed. Do not report comprehension until these sessions happen.

## Verdicts

Functionality: pass for the listed verification cases. Visual clarity: tested screens readable, with recorded friction and independent review pending. AI helpfulness: demonstrated on one complete CRM chain and one incomplete procurement observation, not general self-service acceptance. Accessibility: selected narrow-layout/focus checks only; full assessment not exercised. Integration: current PDLC Spanner pass with verified cleanup; previous transient failure retained.
