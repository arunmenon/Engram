---
schema_version: 1
artifact_id: N-20260928-16
artifact_type: note
producer: triage
run_id: triage-20260928T074501Z-535d
created_at: 2026-09-28T07:59:03Z
input_refs: [{"artifact_id": "post:2104411790138650946", "file_id": null, "sha256": null}, {"artifact_id": "post:2104447612250472570", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:trustifai/typed_evals
claim_cluster: github:trustifai/typed_evals
feeds: ["decision"]
primary_source: https://github.com/TrustifAI/typed_evals
source_commit: ab9fc8a5c3e032ca5732cc0afa318cdd44d331af
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4", "R6"]
memory_stage: evaluation
priority: 1
tags: {"mechanism": ["isotonic calibration", "held-out cutoff selection", "Jev as judge", "tool-call guard"], "workload": ["RAG faithfulness", "hallucination detection", "TRIVIA+"], "lifecycle_stage": ["evaluation"], "cross_cutting": []}
evidence_grade: {"directness": "high: before/after tables on 645 test answers with the protocol written out", "control": "high: same saved Jev judgments scored raw and calibrated, cutoffs chosen on validation and frozen before test, article-level resampling for intervals", "independence": "medium: independent builder (not TypeSafe), public human-labelled dataset (Amazon TRIVIA+)", "reproducibility": "medium: library and protocol pinned at a commit; the saved judgments and fitted artifact are not stated as published", "applicability": "high: it is the exact procedure for turning Jev gate scores into thresholds on our own labels"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Isotonic calibration of Jev scores on a few thousand human labels cuts ECE by about two thirds (0.098 to 0.031) but does not improve ranking or detection F1; it fixes threshold meaning, not accuracy"]}
claim_correction: The posts ask whether "a 0.8 actually mean[s] 0.8"; the repo's answer is narrower than the headline "68% calibration improvement": detection F1 moved 0.5833 to 0.5877 with validated cutoffs, and at the default 0.5 cutoff calibration made detection worse (F1 0.5258 to 0.4478).
---

# Typed Evals (TrustifAI/typed_evals): Jev as a judge, calibrated against human labels on TRIVIA+

- **URL:** https://github.com/TrustifAI/typed_evals
- **Type:** repo (Python library plus a benchmark write-up in docs/BENCHMARK.md)
- **Author / org:** Aaryan Verma (TrustifAI); MIT licence
- **Date:** HEAD `ab9fc8a5c3e032ca5732cc0afa318cdd44d331af` (2026-09-27 19:11:37 +0530, "Remove redundant sources and scope section from BENCHMARK.md"); benchmark "Live benchmark · 27 September 2026"
- **Retrieved:** 2026-09-28, shallow clone `repos/typed_evals`. Read: README.md (Calibration, Benchmark, tool guard sections), docs/BENCHMARK.md in full.
- **Cited by evidence:** @iam_aaryanverma 2026-09-28 https://x.com/iam_aaryanverma/status/2104411790138650946 and https://x.com/iam_aaryanverma/status/2104447612250472570
- **Relevance to a memory stack:** high. We plan Jev thresholds at the write gate, recall gate and staleness check; this shows the calibration step, its protocol, and what it does and does not buy.

## TL;DR
- Jev (`jev-1.13.0` through `typesafe-sdk` 0.7.x) judged faithfulness of 645 TRIVIA+ test answers (421 supported, 224 hallucinated, 358 articles) given only the article and the answer.
- Per-metric isotonic calibration fitted on 2,195 human-labelled training rows reduced ECE from 0.0982 to 0.0313 (68.1%), Brier from 0.2037 to 0.1948 (4.4%), log loss from 0.6286 to 0.5765 (8.3%); intervals "supported all three improvements".
- Detection did not improve: F1 0.5833 (raw, validated cutoff 0.39) vs 0.5877 (calibrated, cutoff 0.2953); accuracy about 72%. Ranking ability "showed no improvement".
- At the default 0.5 cutoff, calibrated scores flagged fewer answers and F1 fell to 0.4478 from 0.5258: a calibrated score needs its own cutoff.
- The library also guards tool calls: `ToolSafety` at a 0.9 threshold raises before the function runs.

## What it claims / describes
Protocol (docs/BENCHMARK.md section 2, verbatim steps):
1. "Judge the answer. Typed Evals' Faithfulness check gave Jev the full article and answer. The question and human label were not part of the judge's input."
2. "Learn the adjustment. Training examples taught Typed Evals how to adjust Jev's scores to better match human judgments."
3. "Choose the cutoffs. Separate cutoffs for raw and calibrated scores were chosen using validation data, aiming for the best detection score (F1). Both were saved before testing."
4. "Test on the same answers. Both versions used the same saved Jev judgments on all 645 test answers. Calibration required no additional judge calls."
5. "Check uncertainty. Repeated samples of whole articles helped estimate how much the results could vary, keeping related answers together."

Data cleaning: training 2,263 -> 2,195 rows (54 duplicate copies, 14 conflicting labels removed), validation 316 -> 308, test 645 kept in full; "no identical article appeared across groups".

Library defaults (README): presets use a 0.5 threshold per metric; the `rag` preset checks faithfulness, answer relevancy and context relevance "in one judge request"; "Missing evidence and judge errors raise by default"; calibration via `EvaluationPipeline` fits "per-metric isotonic curves against representative human pass/fail labels"; "The included labeled datasets are synthetic examples; replace them with human-reviewed labels for your application."

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| ECE | 0.0313 calibrated | 0.0982 raw | TRIVIA+ test, 645 answers | 95% ranges support the gain |
| Brier | 0.1948 | 0.2037 | same | -4.4% |
| log loss | 0.5765 | 0.6286 | same | -8.3% |
| F1, validated cutoffs | 0.5877 (cutoff 0.2953) | 0.5833 (cutoff 0.39) | same | "does not establish a meaningful advantage" |
| accuracy, validated cutoffs | 71.94% | 72.09% | same | |
| F1, default cutoff 0.5 | 0.4478 calibrated | 0.5258 raw | same | calibration worse at a fixed default |
| training / validation rows | 2,195 / 308 | | after de-duplication | |
| tool guard default | ToolSafety threshold 0.9 | | README | |

## Mechanism details you could implement
- Log raw Jev probabilities per question; collect a few hundred to a few thousand human pass/fail labels on our own decisions; fit an isotonic curve per question type; choose the operating cutoff on a separate validation split; freeze both before testing.
- Resample by the grouping unit (article here; repository or document for us) for intervals.
- Re-choose the cutoff after calibration: reusing 0.5 dropped F1 by 0.08.
- Use calibration to make thresholds mean what they say (for escalation budgets and audit), not to expect a better gate.

## Limitations, caveats, counter-evidence
- BENCHMARK.md verdict: "This supports the value of calibration on TRIVIA+. It does not establish a better hallucination detector or superiority over other judges, and results on other data may differ."
- One dataset, one metric (faithfulness), one Jev version; saved judgments and fitted artifact publication not stated.
- Jev's detection F1 of about 0.58 on hallucination is modest; nothing here compares with an LLM judge.

## Takeaways for tuning a memory stack
- Before we set any Jev threshold in a memory gate, fit it on our labels: isotonic per question, validated cutoff, frozen before test. Expect well-behaved probabilities, not more accuracy.
- Report ECE with Brier and log loss; a large ECE drop can coexist with almost no Brier change.

## Open questions
- How many labels are needed per question type for a stable isotonic fit on our decisions?
- Does calibration transfer across Jev versions (`jev-latest` drift)?

## Grading and labels
- Directness high; control high; independence medium; reproducibility medium; applicability high.
- Pillars: R9 primary (Jev as an implementation of a judge and gate), R4 and R6 secondary. Memory stage: evaluation. Priority 1. Product named: Jev.
- Beliefs: supports B14 (vendor calibration not established; fit thresholds locally): an independent measurement against human labels finds raw ECE 0.098 and shows local fitting reduces it; would create the "calibration fixes meaning, not accuracy" belief.
- Contradiction rows: none.

## Origin chain
- Posts 2104411790138650946 and 2104447612250472570 (@iam_aaryanverma, author) -> repo TrustifAI/typed_evals@ab9fc8a -> docs/BENCHMARK.md sections 1 to 4, README "Calibration" and "Benchmark: TRIVIA+" -> this note.
- Independence: TRIVIA+ is an Amazon Science dataset with human labels, unrelated to the typed-decisions teacher; different from the Sentry and LangChain Jev-judge reports (N-CAT-27, N-20260926-10).
