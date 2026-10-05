---
schema_version: 1
artifact_id: N-20260929-25
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104693376222470543", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.27176
claim_cluster: arxiv:2609.27176
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.27176
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R6
pillar_secondary: ["R9"]
memory_stage: evaluation
tags: {"mechanism": ["benchmark-contamination", "controlled-exposure", "difference-in-differences", "lora-fine-tuning", "private-key-association"], "workload": ["sqlite", "python-transformations", "four-choice-selection"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["leakage", "causal-estimation", "bootstrap-ci", "reproducibility-ledger"]}
evidence_grade: {"directness": "medium: directly measures score inflation from exposure, but for LoRA post-training on private key-value associations, not for memory-system benchmarks or pretraining contamination", "control": "high: pre/post difference-in-differences against a balanced no-key control, exact balance of truth rank and display position, family-clustered bootstrap with 10,000 replicates", "independence": "low: single author, single study, no replication; generative AI used for design, code and writing (AI Use Statement)", "reproducibility": "medium: full task catalog, prompts, hyperparameters, seeds and SHA-256 digests in appendices; no code or data URL found", "applicability": "low: four-choice synthetic tasks with memorized keys; relevant to us only as magnitude context for leakage and for fine-tuning a decision model on our own labels (inference)"}
beliefs_affected: {"supports": ["B19"], "contradicts": [], "would_create": ["Controlled exposure to benchmark-specific private information moved four-choice accuracy by +7.17 to +27.31 pp (all four 95% CIs exclude zero) in one LoRA study; memory-stack results on public test sets (LoCoMo, LongMemEval) or on items overlapping a decision model's fine-tuning labels should be checked against fresh held-out variants before gains are trusted"]}
claim_correction: none
---

# LeakScale: Estimating the Causal Effect of Benchmark Exposure

- **URL:** https://arxiv.org/abs/2609.27176
- **Type:** paper (cs.CL), CC BY 4.0
- **Author / org:** Divyansh Singh, University of Florida
- **Date:** v1 2026-09-23; v2 2026-09-24
- **Retrieved:** 2026-09-29, arXiv v2 (abstract page, HTML, PDF pages 1 to 20 read; appendix pages after 20 not read)
- **Cited by evidence:** X post 2104693376222470543 by @mrru5s3ll, https://x.com/mrru5s3ll/status/2104693376222470543 (post text not re-read; summary given by the triage agent)
- **Relevance to a memory stack:** low to medium. Not about memory systems. Useful as a controlled estimate of how much exposure to benchmark-specific information can move a score, which bears on trusting LoCoMo/LongMemEval numbers and on evaluating any decision model we fine-tune on our own labels.

## TL;DR
- Design: fresh executable task families each need a private key -> value association that is not derivable from the public task. 512 families per domain get supervised key -> value records in LoRA training (C2); 512 get none (C0). Both are evaluated before and after adaptation; the estimate is a difference-in-differences (Eq. 3).
- Result (Table 2): exposure-attributable gains of +7.17 pp (Qwen3-4B-Instruct-2507, SQL), +27.31 pp (Qwen3-4B, Python), +12.92 pp (Gemma 4 31B, SQL), +10.14 pp (Gemma 4 31B, Python); "All four 95% confidence intervals exclude zero." Unweighted mean +14.39 pp.
- The control matters: C0 accuracy falls by -2.34 points on average after adaptation (Python C0 drops 25.55 -> 19.81 for Qwen, 27.25 -> 22.50 for Gemma), so a treated-only before/after comparison would be wrong (Section 5.2).
- Scope (Section 4.3): measures "a controlled post-training exposure regimen", not "naturally occurring web-scale contamination"; one adapter training realization per cell; two models and two domains "do not establish universality".
- Post claim matches the source (2,048 families, SQL/Python, four-choice, private key, LoRA vs matched no-key control, Qwen3-4B and Gemma 4 31B, 262,144 generations, 7.17 to 27.31, all CIs exclude zero). No claim correction. Scope note: "benchmark contamination" here means 32-times-repeated supervised exposure to the answer key via LoRA, with adapter strength and temperature tuned on development families.

## What it claims / describes
**Estimand (Section 2).** For model m, domain d, condition c in {C0, C2}, state s in {Base, Adapted}: tau(m,d) = (Y_C2,A - Y_C2,B) - (Y_C0,A - Y_C0,B). Correctness per draw is whether the hidden-fixture oracle accepts the rendered artifact of the chosen candidate (Eq. 2). Unit of inference is the family.

**Instrument (Section 3, Appendix A, C).** Each family: public task x_f, opaque policy key k_f, four displayed candidates V_f, private association g_f(k_f) = v*_f. Certification (Eq. 4, 6): the correct candidate passes all hidden fixtures, each alternative has utility at most 0.75 (fails at least a quarter). SQL: 8 hidden SQLite databases per task, same three-table schema; candidates shown as opaque equal-length handles. Python: 16 hidden fixture sets of 16 records; literals displayed directly. 32 structural shapes per domain (Tables 3, 4), 16 C0 and 16 C2 families per shape. Allocation is deterministic, not randomized, balancing truth rank and display position. Source audit "finds zero normalized content overlap with earlier benchmark sources".

**Evaluation prompt (Appendix B.1, verbatim system message).** "Return one JSON object matching the supplied schema. Select exactly one of the candidate registered values. Do not add explanation or extra keys." Strict JSON-schema enum over the four candidates; non-thinking mode; 64-token cap with one 128-token retry for length-terminated answers; malformed answers score zero (intention-to-treat). These are the paper's model-facing prompts, not instructions to the reader.

**Adaptation (Appendix D).** Two records per C2 family (exact public-benchmark form plus a direct registry lookup), 1,024 physical target records, each repeated 32 times = 32,768 target optimizer examples per cell. Background (non-code, lexically screened) at least 10x target tokens and preservation records at least 2x target tokens (Eq. 9, Table 6). No C0 key in any corpus ("c0_training_records=0", independent audit zero matches). BF16 LoRA rank 32, alpha 64, zero dropout, targets q/k/v/o/gate/up/down_proj; one epoch; fused AdamW; lr 1e-4; max sequence 2,048; effective batch 32. Adapter strength set by scaling LoRA-B; temperature and adapter scale chosen on disjoint development families (Table 7).

**Statistics (Appendix E.1).** Percentile bootstrap, 10,000 replicates, resampling 512 C0 and 512 C2 families independently with replacement, carrying all 32 base and 32 adapted draws per family as a block.

## Numbers

| metric | value | baseline | setup/benchmark (n) | caveat |
|---|---|---|---|---|
| DiD, Qwen3-4B-Instruct-2507, SQL (Table 2) | +7.17 pp [+4.53, +9.78] | Base C0 24.41%, Adapted C0 25.40%, Base C2 25.16%, Adapted C2 33.32% | 512 families x 32 draws per condition-state cell | temp 1.5, adapter scale 0.28125 |
| DiD, Qwen3-4B, Python | +27.31 pp [+22.86, +31.75] | 25.55%, 19.81%, 25.66%, 47.24% | same | temp 1.5, scale 0.43750 |
| DiD, Gemma 4 31B, SQL | +12.92 pp [+8.72, +17.13] | 24.85%, 24.98%, 24.81%, 37.87% | same | temp 1.8, scale 0.43750 |
| DiD, Gemma 4 31B, Python | +10.14 pp [+7.26, +13.18] | 27.25%, 22.50%, 24.84%, 30.23% | same | temp 0.7, scale 0.28125 |
| Mean effect | +14.39 pp (unweighted) | | 4 cells | "cross-cell averages are descriptive" |
| Starting accuracy C0 vs C2 | 25.52% vs 25.12% | chance 25% | aggregate | |
| Adaptation drift | C0 -2.34 points, C2 +12.05 points on average | | Section 5.2 | |
| Correct generations (Table 11), C0/C2 of 16,384 each | Qwen SQL base 4,000/4,122, adapted 4,162/5,459; Qwen Python base 4,186/4,204, adapted 3,246/7,739; Gemma SQL base 4,071/4,065, adapted 4,093/6,204; Gemma Python base 4,465/4,069, adapted 3,687/4,953 | | | |
| Family-accuracy medians, adapted C2 (Table 12) | Qwen SQL 18.75, Qwen Python 46.88, Gemma SQL 37.50, Gemma Python 15.63 | base medians mostly 0.00 | | success varies strongly by family |
| Within-stratum DiD (Table 13) | all 16 truth-rank and all 16 display-position estimates positive; range 3.61 (Gemma Python, rank 0) to 33.40 (Qwen Python, position 2) | | 128 families per stratum per condition | descriptive, no CIs |
| Per-shape SQL DiD (Table 14) | Qwen 0.00 (kind_exclusion) to 22.46 (score_band); Gemma 8.98 to 21.09 (partial table read) | | 16 families per shape per condition | diagnostic only |
| Generations | 262,144 | | 1,024 families per domain (512 C0 + 512 C2, Table 1) x 2 domains x 2 models x 2 states x 32 draws | all completed "without protocol failure" |
| Optimizer examples per cell (Table 5) | Qwen SQL 284,602; Qwen Python 159,501; Gemma SQL 300,038; Gemma Python 173,008 | | target 32,768 in each | |
| Training (Table 8): steps, final loss, runtime h | Qwen SQL 8,894, 0.01676, 2.65; Qwen Python 4,985, 0.02532, 0.83; Gemma SQL 9,377, 0.01670, 20.29; Gemma Python 5,407, 0.02397, 11.32 | | one accelerator per run | |
| Trainable parameters (Gemma) | 244,858,880 | | 820 language-projection tensors | |

## Mechanism details you could implement
- **Exposure DiD for our own evals.** When a model or memory store may have seen evaluation-specific information, keep a matched no-exposure group of items built the same way, measure both groups before and after, and report (treated change) minus (control change). A treated-only before/after comparison confounds exposure with general drift (here C0 moved -2.34 points).
- **Non-derivable private association.** Items whose correct answer depends on information absent from the public prompt make exposure measurable: chance-level before exposure (about 25% for four choices), so any lift is attributable to access.
- **Family-clustered bootstrap.** Resample items (families), not generations; keep repeated draws and before/after pairs as a block. 10,000 replicates, 2.5th and 97.5th percentiles.
- **Certification by execution.** Grade by hidden-fixture execution, and require every wrong option to fail at least 25% of fixtures, so correctness is never inferred from surface form.
- **Reproducibility ledger.** Seeds (source 20263403, training 20263411, inference 20263421), source-tree SHA-256, model/tokenizer/chat-template/corpus/adapter digests (Appendix A, D.5, Table 9). A template for our own eval manifests (R1/R6).

## Limitations, caveats, counter-evidence
- Author-stated (Section 4.3): post-training exposure only, not web-scale or pretraining contamination; four-choice semantic decisions, not unrestricted generation; one adapter training realization per cell, so training-seed variance is not in the CIs; temperatures and adapter scales selected on development families; two models and two domains.
- The exposure is strong: each association record repeated 32 times, supervised in the exact evaluation form plus a direct lookup form. Natural contamination is usually a few copies (inference). The paper does not vary dose (the R1/R2 paraphrase rings are generated but not used in reported results).
- The tasks are pure memorization of arbitrary key -> value pairs; the effect size says how much a memorized answer key helps, not how much seeing a benchmark helps on items requiring reasoning (inference).
- Adaptation hurt control accuracy on Python for both models (about -5 points), which the DiD removes but which signals the adapter perturbs general behavior.
- Single author; AI Use Statement says generative AI was used for "ideation, methodological design, benchmark and software development, debugging, experiment operation, statistical analysis, literature review, figure planning, writing, and typesetting", with authors verifying against artifacts.
- No code or data URL found in the PDF or abstract page, despite digests.
- Applicability to memory benchmarks (LoCoMo, LongMemEval) is an extrapolation; the paper does not test them (inference).
- No instruction-bearing content aimed at AI agents was found. The evaluation prompts in Appendix B are part of the method description.
- Note on retrieval: the WebFetch summarizer returned a fabricated first abstract sentence for the PDF; all quotes here were taken from the PDF pages read directly.

## Takeaways for tuning a memory stack
- Do not trust small memory-benchmark deltas on public test sets without an exposure control; this study shows exposure-driven gains of 7 to 27 points in a controlled setting, far larger than typical memory-system deltas of 2 to 5 points (e.g. B4's ~2 points; comparison is inference).
- If we fine-tune a System One decision model (R9) on our own labeled decisions, hold out items that share no keys, entities or phrasings with training records, and report a DiD against a matched unexposed set.
- For our PDLC memory benchmark: keep a private, never-published split and generate fresh variants per release (the paper's "exposure lifecycle" framing in Section 7).
- Use family-clustered bootstrap and report integer counts per cell, as in Table 11.

## Open questions
- Dose response: how does the effect scale with repeat count (32 here) and with paraphrased rather than exact-form exposure? Not measured.
- Does the effect hold for items requiring multi-hop recall over long histories, as in memory benchmarks? Not tested.
- How much of LoCoMo or LongMemEval is present in current base models' training data, and what DiD would a fresh-variant control show? Not addressed by this paper.
- Training-seed variance is unmeasured.

## Grading and labels
- **Directness:** medium. Measures exposure-driven score inflation directly, but on LoRA post-training with memorized keys, not memory benchmarks.
- **Control:** high. Balanced no-key control, pre/post DiD, deterministic balance, family-clustered bootstrap.
- **Independence:** low. Single author, no replication.
- **Reproducibility:** medium. Full appendices and digests; no public code link found.
- **Applicability:** low. Synthetic four-choice tasks; relevant as magnitude context and to fine-tuning a decision model.
- **Pillars:** R6 primary (leakage, evaluation integrity); R9 secondary (fine-tuning decision models on our own decisions creates the same exposure risk).
- **Stage:** evaluation.
- **Tags:** mechanism benchmark-contamination, controlled-exposure, DiD, LoRA; workload SQLite, Python transformations, four-choice; lifecycle evaluation; cross-cutting leakage, causal estimation, bootstrap CI, reproducibility ledger.
- **B19 supports (context only):** shows leakage can move scores by 7 to 27 pp; it is not evidence about our harness.
- **B20:** not affected (this is a primary read and the post claim held up).
- **Would create:** memory-stack results on public test sets or on items overlapping fine-tuning labels need a fresh-variant exposure control (grade: lead).
- No contradiction with any belief.

## Origin chain
@mrru5s3ll post 2104693376222470543 -> https://arxiv.org/abs/2609.27176 (v2) -> PDF Table 2 (main effects), Section 4.3 (scope), Section 5.2 (control trajectory), Appendix D (adaptation), Appendix E Tables 10 to 14 (statistics). Single-author study; no independent replication or third-party re-analysis found.
