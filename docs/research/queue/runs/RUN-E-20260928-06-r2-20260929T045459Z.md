---
schema_version: 1
artifact_id: RUN-E-20260928-06-r2-20260929T045459Z
artifact_type: run_result
producer: executor
run_id: E-20260928-06-r2-20260929T041426Z
created_at: 2026-09-29T04:54:59Z
input_refs:
  - {artifact_id: E-20260928-06-r2, file_id: 1Gk7I_hW7PrvVyplusSK9ohLV44JnE6-g, sha256: 866d2f63c1486f2fe27bb0ab1b0873c65395d5a30210bdc755f9fc9d92f243ba}
supersedes: null
idempotency_key: run:E-20260928-06-r2:20260929T045459Z
status: complete
---
# E-20260928-06-r2 and H5: Jev as the write gate, with the option-name check

We asked Jev, TypeSafe's hosted decision model, two questions about 90 memories our extractor pulled from public LoCoMo chat transcripts: "does this quote support this memory?" and "what kind of source is it?". We asked each question 48 ways (4,320 calls, about 17 US cents). Two things came out. First, Jev partly answers from the option label rather than the definition behind it: when we swapped which definition "yes" and "no" stood for, Jev changed its answer on 19% of items. Neutral labels (random strings) removed that effect with no loss of accuracy. Second, and more important for Engram, Jev is not a useful gate here. It said "supports" for almost every memory, including the doubtful ones, and it separated good from bad memories worse than the extractor's own confidence score. It is also badly calibrated. So H5 is killed on this data: do not put Jev in front of the write path as a quality gate. If Jev is used anywhere with named options, use neutral option names and put the meaning in the definitions. Recommended next step: keep the extractor's confidence as the gate for now and test a cheaper alternative the discovery plan names (a small NLI model or an open decision model) on these same 90 items, which cost nothing to relabel.

## Numbers

### Naming audit (spec E-20260928-06-r2, Jev jev-1.13.0, n = 90 items, G = 76 source sessions)

Excess sensitivity E = flip rate under reassigned option names minus the test-retest floor. Bounds are from a 10,000-resample cluster bootstrap over sessions.

| Template | Names | Flip rate | Floor | E | 97.5% lower | 95% upper |
|---|---|---|---|---|---|---|
| quote supports item (2 options) | natural (yes/no) | 0.189 | 0.000 | **0.189** | 0.136 | 0.238 |
| | random strings | 0.000 | 0.006 | -0.006 | -0.018 | 0.000 |
| | letters A/B | 0.011 | 0.000 | 0.011 | 0.000 | 0.027 |
| source type (4 options) | natural | 0.100 | 0.017 | 0.083 | 0.046 | 0.116 |
| | random strings | 0.050 | 0.022 | 0.028 | 0.008 | 0.048 |
| | letters | 0.046 | 0.028 | 0.019 | -0.008 | 0.043 |

Mitigation M = E[natural] minus E[random]: quote-supports 0.194 (97.5% lower 0.138); source-type 0.056 (lower 0.017).

Quality against gold (aligned names, run 1, both orders): quote-supports binary F1 natural 0.767, random 0.765, paired difference +0.005 (95% lower bound 0.000); source-type macro-F1 natural 0.558, random 0.564, difference +0.018 (lower 0.000). Macro-F1 excludes `tool_result` and `imported`, which have no gold examples in LoCoMo.

**Spec rule (`verdict.json`): positive.** Risk confirmed on quote-supports (lower bound 0.136 > 0.10), neither confirmed nor excluded on source-type (0.083, upper bound 0.116), neutral names mitigate on quote-supports and are non-inferior on both, E[random] upper bounds below 0.10 on both. Confirmatory (G = 76 >= 30). By the spec's outcome text: rewrite every Noul and Choice template in H5 and H10 with neutral option names and rubric-carried meaning.

### H5 (discovery plan): Jev's gate score against the extractor's confidence

Gate score: Jev P(supports) on the current H5 wording (natural names, aligned, run 1, canonical order), taken from the same calls. Threshold fitted to maximise F1 on half the sessions, tested on the other half.

| | Jev | Extractor confidence |
|---|---|---|
| AUC, all 90 items | 0.627 | **0.768** |
| Test-half F1, primary fold (fit 42, test 48 items) | 0.810 | 0.824 |
| Test-half precision / recall | 0.70 / 0.97 | 0.80 / 0.85 |
| Test-half AUC | 0.521 | 0.859 |
| Test-half ECE (10 bins) | **0.306** | 0.179 |
| Swapped fold test F1 | 0.698 | 0.721 |

F1 difference Jev minus confidence on the test half: -0.013, 95% interval [-0.105, +0.081], one-sided 95% lower bound -0.090. **H5 rule (`h5_verdict.json`): killed** on both grounds (not better than confidence; ECE 0.31 > 0.15).

Why: Jev's mean P(supports) is 0.92 in every bucket (obvious 0.92, ambiguous 0.92, no-fit 0.92), while gold "supports" is 28/30, 12/30 and 15/30. At the default 0.5 cut Jev accepts 88 of 90 items (precision 0.63, recall 1.00).

## Weaker than the spec wanted

- **Model labels, not people.** Gold comes from Claude (claude-opus-5-5) labels reviewed by Codex (gpt-6-astra), at most 3 rounds, per policy v2. First-pass agreement on "supports" was low (kappa 0.30) and rose to 0.98 mostly because Claude converged on Codex's reading, so the final agreement overstates independence. One row is contested.
- **Jev only.** The Laya-0.4B read-out was not run: its licence has not been confirmed from a frozen model-card file.
- **Two-option Choice, not native Noul.** Noul has no option names, so the yes/no question is sent as a two-option Choice (accepted by the CTO in the queue). The H5 gate score comes from that Choice rendering, not a native Noul call.
- **Wording.** The rubric wording was drafted by the executor from jev-typed-decisions.md A1; the CTO accepted it as H5's wording in the queue.
- **Payload check fixed after the run.** The runner's delivery check counted each option name as one token, so the random names (5 more billed tokens) failed a 4-token allowance on all 90 quote-supports items. Billed input tokens were identical across every cell within a name set, so nothing was dropped. The check was recomputed offline with a real tokenizer (tiktoken o200k_base; Jev's own tokenizer is not published): 0 of 180 item-template groups invalid. The runner's original flags are kept in `invalid_items_runner.csv` and `payload_check_runner`. The relative check still cannot detect a rubric lost identically in every cell (REV-20260928-24).
- **Noise floor.** H5's own F1 noise floor was never measured, so the provisional nf = 0.05 was used.
- **Calibration numbers in `f1_ece.csv`.** The naming scorer's ECE column compares P(supports) with "prediction correct" rather than with "gold is supports"; use the ECE in `h5_score.json`, which is computed against gold. The column is reported, not decisive.
- **H5 sample.** 90 items is small; each test half is 42 to 48 items and the bounds are wide. The extractor's confidence takes 23 distinct values, so its thresholds are coarse. The extraction used gpt-5.6-terra; 41 of 272 LoCoMo sessions failed when OpenAI credits ran out and were not retried.
- **Spec gates.** The spec's policy gate (challenger review outcome, accepted decision) was replaced by the CTO's fast-track queue and policy v2.

## Files

`calls.jsonl` (every call, answers, probabilities, billed tokens, latency), `flips.csv`, `mitigation.csv`, `f1_ece.csv`, `verdict.json` (spec rule), `h5_score.json` and `h5_verdict.json` (H5), `invalid_items.csv` (after recheck, empty), `invalid_items_runner.csv`, `models.lock.json`, `run_manifest.json`, `receipts.sha256`. Commands: `gate_eval.naming_audit`, `gate_eval.payload_recheck`, `gate_eval.naming_score`, `gate_eval.h5_score` from `harness/`.


## Run manifest

```json
{
 "G": 76,
 "budget": {
  "calls": 4320,
  "caps": {
   "calls": 9072,
   "cost_usd": 2000.0,
   "tokens": 500000000,
   "wall_clock_s": 86400.0
  },
  "cost_usd": 0.0,
  "tokens": 4118326
 },
 "bundle": {
  "billed_input_tokens": 3911892,
  "billed_output_tokens": 206434,
  "calls": 4320,
  "dataset": "H5-labelled-90",
  "dataset_manifest_sha256": "a10f6655cb23d4dafbb86e276f77d6e3972805ebae18763fb71d8b5536acae8e",
  "ended_at": "2026-09-29T04:45:31Z",
  "extra_outputs": [
   "h5_score.json",
   "h5_verdict.json"
  ],
  "finalised_at": "2026-09-29T04:54:59Z",
  "harness_commit": "3ce0cc231d3ddb0013b5aa6ac276fe6ddba64c84",
  "labels": "model labels (Claude claude-opus-5-5 labels, Codex gpt-6-astra review, max 3 rounds), used as gold per policy v2",
  "latency_ms_p50": 375.53,
  "latency_ms_p95": 572.66,
  "model_pins": {
   "jev": "jev-1.13.0 (requested and reported)",
   "laya": "not run: licence not confirmed from a frozen model-card file"
  },
  "post_run_fixes": [
   "payload check recomputed offline with tiktoken o200k_base name-token counts (gate_eval.payload_recheck); runner's crude count had flagged 1,620 rows; runner verdicts kept as payload_check_runner and invalid_items_runner.csv"
  ],
  "run_id": "E-20260928-06-r2-20260929T041426Z",
  "spec_file_id": "1Gk7I_hW7PrvVyplusSK9ohLV44JnE6-g",
  "spec_id": "E-20260928-06-r2",
  "spec_sha256": "866d2f63c1486f2fe27bb0ab1b0873c65395d5a30210bdc755f9fc9d92f243ba",
  "started_at": "2026-09-29T04:14:26Z",
  "status": "complete",
  "usd_basis": "input tokens x 0.042 USD per million (Jev list rate used by genigrep da10c5e); output tokens not priced separately",
  "usd_estimate": 0.1643
 },
 "call_count": 4320,
 "command": "/Users/arunmenon/MemoryRSI-Signals/work/executor-engram/harness/gate_eval/naming_audit.py --manifest /Users/arunmenon/MemoryRSI-Signals/work/datasets/frozen/H5-labelled-90/manifest.json --templates templates/naming_audit/ --models locks/E-20260928-06-r2.models.lock.json --policy /Users/arunmenon/MemoryRSI-Signals/desk/policy-v2.md --out ../runs/E-20260928-06-r2-20260929T041426Z",
 "dataset": "H5-labelled-90",
 "dataset_manifest_sha256": "a10f6655cb23d4dafbb86e276f77d6e3972805ebae18763fb71d8b5536acae8e",
 "ended_at": "2026-09-29T04:45:31Z",
 "git_clean": true,
 "harness_commit": "3ce0cc231d3ddb0013b5aa6ac276fe6ddba64c84",
 "items_per_document_distribution": [
  3,
  3,
  2,
  2,
  2,
  2,
  2,
  2,
  2,
  2,
  2,
  2,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1,
  1
 ],
 "mean_cluster_size": 1.1842105263157894,
 "models_lock": {
  "api_endpoint": "https://api.typesafe.ai/v1/systemone",
  "api_version": "v1",
  "choice_classes": [
   {
    "rubric_id": "user_stated"
   },
   {
    "rubric_id": "tool_result"
   },
   {
    "rubric_id": "inferred"
   },
   {
    "rubric_id": "imported"
   }
  ],
  "decoding": {
   "note": "TypeSafe exposes no decoding parameters on /v1/systemone; record the served model version instead"
  },
  "jev_model": "jev-1.13.0",
  "jev_model_version_pinned": "jev-1.13.0",
  "laya": {
   "included": false,
   "reason": "licence not confirmed from a frozen model-card file (E-20260928-06-r2 arms)"
  },
  "pinned_from": "first response 2026-09-29: request jev-latest reported model jev-1.13.0",
  "template_sha256": {
   "choice_source_type.json": "3b52d37326ff84b6f772d284d9c2050db7c91dd052ae6b44ca24942bfaa62317",
   "noul_quote_supports_item.json": "69aadbbe7f75022e402688f35b911d9905b5ff26d1a118ce88c9a3bb74e25665"
  }
 },
 "n_items_this_run": 90,
 "payload_check_limitation": "relative token check only; identical rubric loss in all cells is undetectable (REV-20260928-24)",
 "policy_snapshot": {
  "budget_per_run": {
   "cost_usd": 2000.0,
   "tokens": 500000000,
   "wall_clock_h": 24.0
  },
  "budget_per_week": {
   "cost_usd": 10000.0,
   "runs": 1000
  },
  "concurrency": 1,
  "dogfood_tenants_named": [],
  "permitted_datasets": "[public benchmarks, seeded fixtures, the Engram repository's own history]",
  "policy_sha256": "b22dfab07df9e60f4952ddd3bd2f9467dff1f3fcf65fa6306f51945ec42ec191",
  "policy_version": "2.0",
  "status": "set"
 },
 "render_only": false,
 "rows_ok": 4320,
 "rows_rendered": 4320,
 "spec": "E-20260928-06-r2",
 "started_at": "2026-09-29T04:14:26Z",
 "stop_reason": null,
 "template_render_modes": {
  "choice_source_type": "choice",
  "noul_quote_supports_item": "choice_two_option"
 }
}
```
