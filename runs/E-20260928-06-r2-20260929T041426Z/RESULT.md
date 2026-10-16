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
