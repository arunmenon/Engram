---
schema_version: 1
artifact_id: N-20260930-23
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105171273466974662", "file_id": null, "sha256": null}, {"artifact_id": "post:2105137477233320312", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:magazine.sebastianraschka.com/p/classifier-history-and-jev
claim_cluster: url:magazine.sebastianraschka.com/p/classifier-history-and-jev
feeds: ["decision", "memory"]
primary_source: https://magazine.sebastianraschka.com/p/classifier-history-and-jev
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R4"]
memory_stage: none
priority: 1
tags: {"mechanism": ["zero-shot typed decision vs fine-tuned classifier", "choice vs noul formulation", "temperature scaling", "calibration-rewarded RL"], "workload": ["IMDb sentiment, 25,000 test reviews"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high", "control": "medium", "independence": "high", "reproducibility": "medium", "applicability": "low"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Two open-weight Jev-like models trail hosted Jev on the same zero-shot task by 4 to 14 points (Laya 92.33%, CLM 82.90%, Jev 96.47% on IMDb), measured by an independent author"]}
claim_correction: none
---

# Language Models for Text Classification: From Bag-of-Words to Jev (Sebastian Raschka, Ahead of AI)

- **URL:** https://magazine.sebastianraschka.com/p/classifier-history-and-jev
- **Type:** essay with hands-on experiments
- **Author / org:** Sebastian Raschka (independent; Ahead of AI newsletter)
- **Date:** 2026-09-29
- **Retrieved:** 2026-09-30 (local copy of the page: repos/_src_raschka_jev.html). The Jev run output lines and the Laya and CLM sentences were checked in the raw page; the rest was read through a summarising fetch.
- **Cited by evidence:** https://x.com/hugobowne/status/2105171273466974662 (@hugobowne), https://x.com/bykimdohoon/status/2105137477233320312 (@bykimdohoon). Both digests of 2026-09-30.
- **Relevance to a memory stack:** low to medium. The task is sentiment classification, far from memory. It earns a note as an independent measurement: a well-known educator with no stake ran hosted Jev (TypeSafe), and two open-weight Jev-like models (Laya, Contrastive Language Models), on the same 25,000 items and reports cost and run time.

## TL;DR
- Zero-shot Jev-1.13.0 on the full IMDb test set: "Accuracy 96.47% (24,117 correct)", "Total runtime: 22 minutes 24 seconds", "15,456,663 input tokens, $0.6492 total cost" (Choice formulation). Noul formulation: "Accuracy 96.20% (24,050 correct)".
- His own baselines on IMDb: bag-of-words logistic regression 89.9%, LSTM 85.66%, CNN 90.07%, fine-tuned ModernBERT about 95%, GPT-2 (124M) about 92%.
- Open-weight Jev-likes, run by the author: Contrastive Language Models "its IMDb test accuracy is just 82.90% (over 96.47% in Jev)"; Laya "did better at IMDb (92.33% test accuracy) but then failed the Tetris test even worse."
- Caveat stated by the author: "we don't know if the IMDb test set was part of the training set".
- He does not measure Jev's calibration. The calibration section explains methods and cites a published result for a related training method.
- The posts describe the article accurately. No claim correction.

## What it claims / describes

**Argument.** A history of text classifiers, then Jev-like APIs as a general-purpose zero-shot decision layer between fine-tuned classifiers and chat models. The author's change of mind: from "classifiers used to be my bread & butter; I can easily build this myself" to "wow, this actually works better than I thought". His framing: "it is the ChatGPT moment for classification".

**What he says about how Jev works.** A guess that it is "something small similar to ModernBERT, hence, the low latency"; training data per the vendor's CEO is fully synthetic; the training algorithm is the vendor's "Reinforcement Learning for Calibrated Decisions (RLCD)", details not public. He relates it to the published RLCR method ("Beyond Binary Rewards"), whose reward he gives as R = c - (q - c)^2 with c the correctness and q the stated confidence. "the architecture, algorithm, and training data details are not public".

**Calibration section.** Explains temperature scaling (divide logits by a learned T) and Brier loss. His own ModernBERT experiment: "adding the Brier loss to cross-entropy provided only a very small additional calibration benefit". Cited RLCR result on HotpotQA with Qwen2.5-7B: accuracy 62.1% to 63.0%, ECE 0.37 to 0.03; six-dataset average accuracy 53.9% to 56.2%, ECE 0.46 to 0.21 (these are the RLCR paper's numbers as relayed by the essay, not Jev's).

**Updates appended by the author.** OpenAI announced a Decisions API the same day; readers shared Jev-like alternatives, which he then tried (the Laya and CLM figures above).

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Jev-1.13.0, Choice, IMDb test | 96.47% (24,117 of 25,000) | ModernBERT fine-tuned about 95%; ULMFiT 95.4% (historical) | zero-shot, section 3.3 | possible training-set exposure, per the author |
| Jev-1.13.0, Noul, IMDb test | 96.20% (24,050 of 25,000) | Choice 96.47% | same | formulation changes 67 answers |
| Repeat run, Choice | 96.44% | 96.47% | same | non-determinism attributed to batch-dependent GPU kernels |
| Run time and cost, Choice | 22 min 24 s; 15,456,663 input tokens; $0.6492 | fine-tuned ModernBERT: 23 min training plus 7 min inference | 25,000 reviews | cost is input tokens only |
| Run time and cost, Noul | 23 min 3 s; 15,106,663 input tokens; $0.6345 | | same | as reported by the fetch; not re-checked in the raw page |
| Laya (open weight), IMDb test | 92.33% | Jev 96.47% | author's run | model size and settings not stated in the lines read |
| Contrastive Language Models (open weight), IMDb test | 82.90% | Jev 96.47% | author's run | same |
| Bag-of-words + logistic regression / LSTM / CNN / GPT-2 124M | 89.9% / 85.66% / 90.07% / about 92% | | author's notebooks, sections 1 and 2 | different training budgets |
| Jev calibration (ECE, reliability) | not stated | | | not measured in the essay |

## Mechanism details you could implement
- The same binary decision can be posed as a two-option Choice or as a Noul; here they differed by 0.27 points. Try both on a labelled sample before fixing a question design.
- Expect small run-to-run differences from a hosted decision model (96.47 vs 96.44); store the served answer rather than assuming a rerun reproduces it.
- For a fixed, high-volume, single task with labels, a fine-tuned encoder reaches about the same accuracy at zero marginal API cost after 23 minutes of training; the zero-shot model earns its place when tasks change or labels do not exist.

## Limitations, caveats, counter-evidence
- One dataset, an old and widely circulated one. The author flags possible exposure.
- No calibration measurement of Jev; the calibration numbers in the essay belong to a different published method.
- Laya and CLM settings are not given in the lines read; a different prompt format might change their scores (inference).
- A reader comment relayed by the author says Jev does poorly in non-English languages; no numbers.
- Sentiment classification says little about memory decisions such as "does this replace that".

## Takeaways for tuning a memory stack
- An independent run supports the basic accuracy and cost claims for hosted Jev on an easy public task, and supports a gap between hosted Jev and two open-weight alternatives on that task. Neither transfers to our decisions without our own test.
- Noul versus Choice is a real design variable.
- Replay cannot rely on re-asking the model: keep the answer that was served.

## Open questions
- How do Laya and CLM compare with Jev on decisions that need reading two items against each other? Not tested here.
- Is Jev calibrated on this task? Not measured.

## Grading and labels
- **Directness: high.** The author's own run output is printed in the article.
- **Control: medium.** Same test set across a dozen models; zero-shot and fine-tuned models are compared with different budgets; one dataset.
- **Independence: high.** Author has no stated tie to the vendors compared.
- **Reproducibility: medium.** Notebooks linked for the classical and fine-tuned baselines (github.com/rasbt); the Jev and open-weight runs' scripts were not located in the text read.
- **Applicability: low.** Sentiment classification.
- **Strength:** builder-report.
- **Pillars:** R9 primary (hosted versus open-weight System One models, quality and cost). Secondary R4 (calibration as a precondition for automating a decision). Memory stage: none. Priority 1; also priority 2 (Laya and CLM comparison).
- **Beliefs:**
  - B14 supports: calibration is explained and attributed to the vendor's training method, not shown for Jev.
  - Would create: open-weight Jev-likes trail hosted Jev by 4 to 14 points on this task.
- **Contradiction rows:** none. Note for the reader: N-20260929-09 (JevBench v1.5) and the Ollama note (N-20260930-20) report open models near Jev on aggregate benchmarks; this single-task result points the other way for two specific smaller models. Different models and tasks, so no contradiction is recorded.

## Origin chain
- Posts by @hugobowne and @bykimdohoon -> https://magazine.sebastianraschka.com/p/classifier-history-and-jev -> section 3.3 run output (96.47%, 22 min 24 s, $0.6492), update paragraph (Laya 92.33%, CLM 82.90%) -> this note.
- Independence: independent author. Shares the vendor model with most R9 notes; shares the CLM model with note github-contrastive-lm-clm.md and Laya with several open-weight notes; no shared harness.
