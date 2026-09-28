---
schema_version: 1
artifact_id: N-20260927-20
artifact_type: note
producer: triage
run_id: triage-20260927T074501Z-b34f
created_at: 2026-09-27T07:58:26Z
input_refs: [{"artifact_id": "post:2104094541112582345", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:edgelesssys/privatemode-decisions-benchmark
claim_cluster: github:edgelesssys/privatemode-decisions-benchmark
feeds: ["memory", "decision"]
primary_source: https://github.com/edgelesssys/privatemode-decisions-benchmark
source_commit: f5ecd9f77541b5a5804f7ca7fa0d45ad599aeb84
strength: repo-pinned
pillar_primary: R4
pillar_secondary: ["R6"]
tags: {"mechanism": ["masked-single-pass-choice", "allowed-token-ids", "option-count-ladder", "label-rename-memorisation-control", "reasoning-control-arm"], "workload": ["classification", "intent", "NLI", "document-images"], "lifecycle_stage": ["decide"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: 29 datasets, per-dataset accuracy with replicate spread, paired tests, controls, raw runs released", "control": "high: identical state, option names, order and instruction for every arm; two control arms (embedding floor, same LLM with reasoning); ladders change only option count; rename perturbation", "independence": "low: written by one of the parties compared (Edgeless/Privatemode), stated in the README", "reproducibility": "high: pinned commit, frozen dataset specs, harness, aggregation, raw runs in a release tag", "applicability": "medium: typed decisions with many options are our rerank and routing shape; datasets are public classification, not engineering artifacts"}
beliefs_affected: {"supports": ["B14", "B20"], "contradicts": ["B13"], "would_create": ["A general LLM read out through one masked forward pass (no fine-tuning) matches a purpose-built decision model on accuracy across 28 datasets; letting the same LLM reason beats both on 21 of 28 at about 5 to 22 times the cost"]}
claim_correction: The post (and the article it summarises) says option count affects accuracy more than the choice of system; the one-variable ladders are mixed: on TREC 6 to 42 options Jev falls 0.921 to 0.856, but on MASSIVE 18 to 59 options Jev rises 0.752 to 0.830 (en) and 0.738 to 0.792 (de).
---

# Privatemode Decisions vs TypeSafe Jev vs Laya: a 29-dataset decision-model benchmark with controls

- **URL:** https://github.com/edgelesssys/privatemode-decisions-benchmark (article summarised on X: Privatemode blog, 2026-09-24, not fetched)
- **Type:** repo (benchmark harness and results)
- **Author / org:** Edgeless Systems (Privatemode). "This benchmark was written by one of the parties it compares."
- **Date:** commit f5ecd9f77541b5a5804f7ca7fa0d45ad599aeb84, 2026-09-24 17:49:10 +0200, "Upgrade to Python 3.14"; raw runs in release `runs-2026-09-24`
- **Retrieved:** 2026-09-27 (shallow clone at repos/privatemode-decisions-benchmark). Read: README.md, results/suite.md (per-dataset, overall, pairwise, option bands, ladders, rename excess).
- **Cited by evidence:** @jiangkoumo_ 2026-09-27 https://x.com/jiangkoumo_/status/2104094541112582345 (Chinese summary of the HN-front-page article; pool item)
- **Relevance to a memory stack:** medium-high for R4. The best-controlled public comparison of decision-model implementations so far: same inputs to every arm, replicate noise measured (hosted arms flip up to 3.5% of answers at temperature 0), a reasoning control and an embedding floor.

## TL;DR
- Arms: Privatemode `decisions` library on GLM-5.3-Flash ("one masked forward pass read out of a single logit row", `allowed_token_ids` restricted to option indexes, no fine-tuning); Jev `jev-latest` hosted; Laya 421M (ModernBERT-large + decision head) on a laptop. Controls: `glm-cot` (same GLM, reasoning allowed) and `embed-nn` (Qwen3-Embedding-4B nearest option).
- Accuracy on 28 shared datasets: Jev vs Privatemode 10 wins, 8 ties, 10 losses, median +0.007, Wilcoxon p = 0.6406. Laya behind both (p < 0.001).
- Reasoning wins: glm-cot vs Jev 21 wins / 5 ties / 2 losses, median +0.020, p = 0.0002; cost EUR 0.35 per 1,000 vs Privatemode 0.062 and Jev 0.0156.
- Latency is geography: from Germany Privatemode p50 180 ms vs Jev 264 ms; from a US runner Jev 164 ms vs Privatemode 299 ms. Cost: Jev EUR 0.0156 per 1,000 decisions vs Privatemode 0.0624 (about 4x cheaper).
- Option-count ladders (same examples, one variable) disagree in sign: TREC 6 to 42 hurts every product; MASSIVE 18 to 59 helps Jev (+0.078 en).

## What it claims / describes
"Each arm receives the identical state string, the identical option names in the identical order, and the identical instruction line." Four runs kept separate to avoid contamination: A accuracy (1,000 examples, 2 replicates, concurrency 16); B latency (100 examples, concurrency 1); C control arms; D memorisation (same sample with every option replaced by a frozen synonym). Fairness rules: same connection-pooled HTTP client, same retry policy, examples interleaved, arm order rotating, warmup discarded, an arm's failure to answer counts as wrong. Option sets are frozen per dataset in `datasets/<name>.json` with chance level, majority share and duplicates. Metrics: accuracy, macro F1, ECE and Brier from the probability on the picked option, AUROC and selective accuracy from each vendor's own `confidence`, paired McNemar and bootstrap CIs.

## Numbers

| metric | jev | privatemode | laya | glm-cot | embed-nn | setup | caveat |
|---|---|---|---|---|---|---|---|
| mean normalised accuracy | 0.574 (28 sets) | 0.585 (29) | 0.422 (27) | 0.665 (29) | 0.355 (28) | normalised to majority baseline | |
| mean coverage at 95% accuracy | 0.494 | 0.431 | 0.279 | 0.478 | 0.160 | selective accuracy | |
| median replicate spread | 0.003 | 0.004 | 0.000 | 0.000 | 0.000 | 2 replicates | ties defined as within 0.01 |
| band 2 options (6 sets) | 0.871 | 0.855 | 0.857 | 0.899 | 0.728 | paired sets | |
| band 3 to 6 (8 sets) | 0.736 | 0.720 | 0.669 | 0.756 | 0.487 | | |
| band 7 to 20 (8 sets) | 0.722 | 0.735 | 0.474 | 0.783 | 0.546 | | |
| band 21 to 80 (4 sets) | 0.818 | 0.792 | 0.389 | 0.820 | 0.722 | | |
| band 81+ (1 set) | 0.749 | 0.742 | 0.210 | 0.760 | 0.459 | ledgar | |
| TREC ladder 6 to 42 | 0.921 to 0.856 | 0.912 to 0.796 | 0.884 to 0.512 | 0.930 to 0.768 | 0.366 to 0.506 | same examples | |
| MASSIVE en ladder 18 to 59 | 0.752 to 0.830 | 0.764 to 0.824 | 0.567 to 0.446 | 0.815 to 0.865 | 0.812 to 0.822 | same examples | |
| MASSIVE de ladder 18 to 59 | 0.738 to 0.792 | 0.771 to 0.779 | 0.327 to 0.220 | 0.830 to 0.842 | 0.798 to 0.767 | same examples | |
| banking77 (77 options) | 0.793 | 0.769 | 0.379 | 0.806 | 0.794 | 1,000 examples | embed-nn ties Jev here |
| clinc150 (151 options) | 0.784 | 0.875 (two requests, 719 ms p50) | cannot | 0.879 | 0.628 | | Privatemode reads 128 + 23 options in two parallel requests |
| rvl_cdip scanned docs | cannot | 0.702 | cannot | 0.696 | n/a | images | |
| latency p50 (Germany, all sets) | 251 ms | 152 ms | local | 7.2 s mean | n/a | concurrency 1 | network included |
| EUR per 1,000 decisions | 0.0156 | 0.0624 | local | 0.35 | n/a | billed usage, list prices | |
| rename drop, banking77 | -0.188 | -0.210 | -0.121 | | | frozen synonyms | excess vs median arm: jev -0.000 |

## Mechanism details you could implement
- A decision model without training: number the options in the prompt, prefill `choice_index:`, restrict the next token to the option indexes via `allowed_token_ids`, and read the softmax over those tokens (description from the X summary and README: "one masked forward pass read out of a single logit row").
- Beyond ~128 options, split the logprob readout across parallel identical requests and renormalise.
- Measure replicate noise before comparing arms: hosted arms flipped up to 3.5% of answers between identical temperature-0 runs; treat differences under 0.01 as ties.
- Always include an embedding nearest-option floor and a reasoning arm of the same model.
- Test memorisation with frozen option synonyms and read the drop relative to the median arm.

## Limitations, caveats, counter-evidence
- Written by an interested party (stated). Jev and Laya ran at default settings; the Privatemode prompt "is the library's, not tuned on these datasets".
- Public classification datasets, not engineering decisions; one seed (0).
- Latency depends on data-centre location; the headline latency table was taken on another day than the probe.
- Confidential-computing benefit "Neither is quantified here."
- A synonym rename can change the question (boolq true/false to correct/wrong), so rename drops do not always isolate memorisation.

## Takeaways for tuning a memory stack
- Before paying for a purpose-built decision model, try an open LLM with masked single-pass choice readout on your own options; accuracy parity is plausible.
- Where 250 ms matters, measure from your own region.
- For low-volume, high-stakes decisions, the same LLM with reasoning is better in 21 of 28 datasets: escalate hard cases to reasoning, not to a bigger one-pass model.
- Do not assume more candidates always hurts: in these ladders it depends on the label set.

## Open questions
- Calibration (ECE, Brier) per arm is computed in the harness; the per-dataset calibration table was not read this run.
- Same comparison on engineering-agent decisions (rerank of ADRs, supersession yes/no).

## Grading and labels
- Directness: high. Control: high. Independence: low. Reproducibility: high. Applicability: medium.
- Strength: repo-pinned. Pillar R4 (implementation choice for typed decisions, escalation to reasoning); secondary R6 (benchmark design: replicate noise, controls, ladders, perturbation).
- Beliefs: supports B14 (each vendor's confidence gives different coverage at 95% accuracy; must be measured); supports B20 (the popular summary "option count matters more than the system" narrows on the ladders). Contradicts B13 in part: B13 says "escalation to a larger battery is not automatically better"; here escalating the same model to reasoning was better on 21 of 28 datasets (p = 0.0002). B13 was about a larger question battery in jevmem, not reasoning, so this is a scope contradiction, recorded as an open row.
- Contradiction row: B13, "escalation is not automatically better" vs glm-cot > one-pass arms on 21/28 datasets (median +0.020 to +0.023); open; the two concern different escalation kinds (more typed questions vs reasoning).

## Origin chain
@jiangkoumo_ post 2104094541112582345 (summarising the Privatemode article of 2026-09-24 on the HN front page) -> github.com/edgelesssys/privatemode-decisions-benchmark at f5ecd9f -> README results, results/suite.md overall, pairwise, option bands, ladders, rename -> this note. Independence: interested party; Jev and Laya also appear in Intern-Decision's baselines (`github-internlm-intern-decision.md`) with different suites; Banking77 figure cross-checked in `blog-openrouter-jev-vs-opus-5-banking77.md`.
