# Event-admission impact of pack edits

Issue #87, first narrow slice: event validation and handling (ARCH-1-001). Base d1441c0dbc89160138f7f002a8a19866c6593315; branch fix/87-event-admission-impact.

## Operator flow and scope

An operator assesses an edited ontology pack before adopting its rules. Making an optional event field required can reject new submissions that the previous pack accepted. The existing comparison only checks event names, so it can describe executable rule edits as documentation/vocabulary changes.

This slice adds producer-compatibility diagnostics and corresponding version requirements through existing ChangePlan/API/CLI consumers. There is no new workbench screen or mandatory operator acknowledgement, no activation procedure and no change to the admission validator/writer. The projection worker's existing version gate consumes the result; this does not introduce staged admission at every API startup.

## Comparison policy

Graph application and admission compatibility are separate axes. Contract tightening must not force a graph rebuild or history replay by itself. ChangePlan.kind and pack_changes continue to describe graph application, while a new admission_changes map reports event compatibility. Version requirements use the strongest graph or admission impact for each owning pack, preserving existing normal and pre-1.0 rules.

For the bounded payload-contract language, prove when all formerly valid payloads remain valid. Proven relaxations are additive; potentially restrictive changes are breaking for version purposes and clearly warn about new submissions. The proof is deliberately conservative and structural, not a general schema theorem prover. Required/nullable fields, nested objects and arrays, enum membership, bounds and extra-field behavior must be considered. Non-executable notes, aliases and equivalent explicit defaults must not create rejection warnings.

For edited event declarations, handling is compared with the registry's declared projection/extraction consumers and current admission fallback rules; it is not proof of external runtime availability or tenant activation. Validate those assessments against the real compiled admission policy. Contract addition/removal must acknowledge the core open-event versus domain required-contract policy rather than pretending every absent contract means identical admission behavior.

## Verification and review gates

Public seams: classify_change, real compiled AdmissionPolicy.decide, existing reconcile/version refusal and status serialization. Use fresh declaration copies and actual validators; preserve original pack fixtures, payloads, business expected answers and receipt/duplicate rules. Add one failing behavior then its fix, plus relevant preserved cases. No engine/bundle/tenant fencing bypass or automatic data repair. Link defaults, foreign-contributor attribution, consumer-only processing edits and wider answer-affecting invalidation from #87 remain separate slices. Inert aliases do not implement a live input rewrite. Open-namespace configuration changes themselves remain capability/composition work; declaring new validation inside an already open core namespace is covered here.

Use local isolated worktree checks and at most two independent Fable review calls ($5 cap each), with second only if needed. No cloud, provider product call, deployment or merge is inferred. Python 3.14.2 local verification is distinct from Python 3.12 CI and live backend evidence.

## Implemented behavior and verification

The deterministic comparator now reports `admission_changes` by event, separately from graph application. The existing status API and CLI receive the same serialized plan. The worker refuses insufficient pack versions through its existing gate. A compatible major version for a restrictive admission edit can be adopted without replaying history or changing stored records.

For example, changing `note` from optional to required reports that field by name and warns that new submissions may be rejected. Removing that requirement is compatible. A new optional typed field can still be restrictive when old rules preserved unrestricted extra fields; this case is checked against actual validator decisions. Integer-to-finite-number changes remain conservative because some accepted large integers cannot pass the finite-number validator.

Offline verification on the candidate:

- 33 focused behavior tests, including real compiled admission decisions, normal/pre-1.0 version checks, an existing memory graph preserved across refusal/adoption, and status API output.
- 824 selected regression tests on the final candidate: versioning, admission, payload contracts, authenticated trust, readiness, composition, memory identity, fake-Spanner admission and hex purity. Fake adapters are not live Spanner evidence.
- 2 memory end-to-end controls pass; 4 external cases deliberately deselected.
- Ruff, mypy on the runtime module and diff whitespace check pass.

The first broad test command selected one nonexistent filename and collected no tests; the corrected selection above passed. Local Python3.14 results do not assert Python3.12 CI or live backend behavior. Sources: `output/implementation/ontology-v2/slice87-events/` (local, not published), including red/green witnesses, `regression-final.txt`, `memory-controls-final.txt`, and source hashes in `review-manifest.json`.

## Independent review and disposition

[Fable round 1](event-admission-impact-fable-round1.md) returned **PASS for the bounded scope**, with one low fix recommended. The original report is preserved unchanged. It reports differential checks against real validators and handling decisions plus 77 affected tests. Those bounded samples are not a general correctness proof.

D1: moving an event from core to a domain pack could use the new owner's admission defaults for both sides, understating newly rejected submissions. The correction conservatively classifies an event-owner change as admission-breaking for the new owner. This remains separate from graph kind; existing projection-rule classification still runs. Two real-policy cases (with/without a new contract) fail on the reviewed candidate and pass after correction, including the owning pack's major-version requirement. The suggested real-validator enum-length control was also added and passes.

Fable explicitly stated a second round was unnecessary if that correction landed with its test. One of at most two authorized review calls was used ($2.9891008 reported). No second peer review or exact-final-hash acceptance is claimed: the runtime correction and three added cases were verified by Codex locally. Review hashes and final hashes remain separately recorded. The focused plus existing versioning selection now passes 80 tests.

Still separate: consumer-only processing changes can affect admission; open-namespace setting edits can change eligibility. The original misleading fallback for those settings is not fixed by this slice. Link defaults, contributing-pack attribution and wider evaluation invalidation in #87 remain open. No full activation gate, automatic data migration, live backend/provider or operator comprehension claim is made.

Status: local verification and bounded independent review complete; delivered as a draft PR targeting integration/engram-ontology-v2. No merge or deployment.
