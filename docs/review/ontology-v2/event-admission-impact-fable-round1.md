## Verdict: PASS for the bounded scope, with one low-severity fix recommended

The proof and the handling comparison held up against the real compiled `AdmissionPolicy`. I found one falsely safe classification, in an edge outside the main operator flow. A second review round is not needed if the fix lands with its test.

## What I checked

- **Contract inclusion proof:** I compared `_contract_accepts` with the real compiled validators over 5,112 single-field and 2,450 two-field contract pairs, about 80 payloads each. It proved 394 single-field pairs compatible and none was wrong; the two-field set also had no wrong proofs.
- **Handling:** I compared `classify_change` with real `decide` results over 380 old/new combinations of handling, projection, contract and extraction source. There were no missed rejections when a declaration changed, and no false "breaking" when decisions were identical.
- **Consumer inventory:** `_processing_events` matches how `resolve_bundle` and `compile_admission_policy` derive consumers (projection present; extraction sources plus propose). A core event cannot be declared `ledger_only` or `unsupported` (compile refuses), so the new-event check only needs the contract case.
- **No false replay or rebuild:** `note_admission` only ever notes graph kind `additive`, and `replay_event_types` stayed empty in every admission-only case.
- **Version merging:** breaking admission overrides the pack's graph kind for the bump only; additive never downgrades `mapping`. The pre-1.0 rule is preserved.
- **Downstream:** the only source consumers of the plan are `reconcile`, the status output and the log line. Nothing in `src` reads the plan's `pack_changes`, and I found no strict schema over the change dictionary.
- **Tests:** the optional bounded run gave 77 passed.

## Defect

**D1 (low): an event that moves from core to a domain pack is judged with the new owner's rules on both sides.** `src/context_graph/domain/pack_versioning.py:269-274` and `:284-290`.

- **Witness (reproduced):** old registry is core plus telemetry, with `tool.execute` in core and no contract. New registry removes it from core and declares it in telemetry with a required `meter` field and a projection rule. Old `decide("tool.execute", {})` is allowed; new is rejected.
- **Result:** `admission_changes == {"tool.execute": "additive"}`, no version problems for telemetry 1.0.0 to 1.1.0, and the reason says "review newly eligible submissions".
- **Related case, from reading the code and not run:** a core event with no contract moved to a domain pack with no contract goes from accepted to rejected with no admission entry. The contract is unchanged, so the handling branch at `:303-305` is skipped.
- **Smallest fix:** when `before.pack != after.pack`, call `note_admission("breaking", ...)` with an ownership-changed reason. Alternatively, use `before.pack` for the old side and `after.pack` for the new side, and add the pack change to the gate at `:303`.
- **Verification:** one test from the witness asserting `breaking` and a major-version problem for the new owner.

## Conservative limitations (not defects)

- Type changes (including integer to number), an empty contract added to a core event, and a tightened contract on an already unsupported event are all classified breaking. About 100 sampled single-field pairs were compatible on my samples but unproven.
- `processed` to `ledger_only` is breaking although submissions are still accepted.
- Removing a domain contract emits two breaking reasons for the same event (contract and handling); this is cosmetic.

## Declared-separate residuals, confirmed still open

- **Consumer-only edits:** removing the only extraction source turns an accepted event into `unsupported` with plan kind `additive`, no admission entry, and a minor bump suffices. Removing the projection rule does the same but is caught as graph `breaking`.
- **Open-namespace removal:** `tool.extra` goes from accepted to rejected and the only reason given is "documentation or vocabulary changed". This fallback text is unchanged from base, but it is misleading for whichever slice picks this up.

## Evidence limits

- The enum-plus-length branch of the proof assumes pydantic enforces length bounds on enum members. That holds on the local 2.13.5, but no test pins it; a real-validator test for an over-length enum member would guard it.
- I did not rerun the 821-test regression, ruff or mypy. Everything ran on local Python 3.14 with the memory backend; nothing was checked on Python 3.12 CI, a live backend, a provider or the UI.
- The differential grammars are bounded: one or two fields, shallow nesting. They are evidence, not a proof.
- I made no edits; all probes ran inline.
