---
schema_version: 1
artifact_id: N-SURVEY-20261002-02
artifact_type: note
producer: triage
run_id: survey-20261002T054505Z-3d1e
created_at: 2026-10-02T06:30:00Z
idempotency_key: note:survey:arxiv:2609.08279
input_refs: []
pillar_primary: R2
pillar_secondary: [R3]
memory_stage: forgetting
priority: 4
beliefs_affected:
  supports: [B6]
  contradicts: []
evidence:
  directness: {level: medium, reason: "Measures eviction loss vs a no-evict reference on the same reader; it audits loss composition, not an accuracy gain from forgetting."}
  control: {level: high, reason: "Per-question paired restore intervention, frozen protocol, cluster bootstrap with Holm correction, positive (destructive) control; H2 amended after freeze."}
  independence: {level: medium, reason: "Single author (Megagon Labs), no system to sell; but reader and judge are the same model (GPT-4o-mini)."}
  reproducibility: {level: high, reason: "Dataset pinned by sha256, temperature 0, per-question records and code released (App. B)."}
  applicability: {level: low, reason: "Conversational QA (LongMemEval-S), not build-time coding agents; the restore-counterfactual instrument transfers (inference)."}
source_url: https://arxiv.org/abs/2609.08279
found_via: survey
---

# What Eviction Destroys: A Restore-Counterfactual Audit of Forgetting in Agent Memory

- **URL:** https://arxiv.org/abs/2609.08279
- **Type:** paper
- **Author / org:** Chen Shen, Megagon Labs
- **Date:** arXiv v1 08 Sep 2026
- **Retrieved:** 2026-10-02 (local copy: /Users/arunmenon/MemoryRSI-Signals/work/survey/survey-20261002T054505Z-3d1e/out/log/src/2609.08279.html)
- **Cited by evidence:** survey R2
- **Relevance to a memory stack:** high, it gives a cheap per-question instrument to tell whether a forgetting policy's loss is irreversible (retention problem) or recoverable (retrieval problem).

## TL;DR
- Four eviction policies (FIFO, random, redundancy-aware, LLM-importance) plus a no-evict reference and a destructive control, on LongMemEval-S (470 evidence-labeled questions, oracle-answerable N=336), budgets 8k/30k/80k against ~102k-token histories.
- No evicting policy beats no-evict on errors at any budget: no-evict err 95/336; best evicting cell is LLM-importance 80k err 102/332.
- Under realistic top-k retrieval at 80k, "the irreversible share among errors corrected by restoration is 0.67–0.73 for FIFO, random, and redundancy-aware eviction, compared with 0.60 for LLM-importance. At 8k tokens, it reaches 1.00 for all four policies."
- At matched accuracy, no policy differs in irreversible rate "at a resolution of 1.2–6 percentage points"; the destructive control is detected.
- Budget-accuracy frontiers are not comparable unless the retrieval regime is reported.

## What it claims / describes
The restore counterfactual reinstates a question's gold evidence into the read-time context after a policy has evicted, reruns the same frozen reader, and classifies each oracle-answerable error as irreversible (gold evicted, restore fixes it), recoverable (gold retained but missed by retrieval, restore fixes it) or residual (still wrong after restore). Two retrieval regimes: (a) forced-gold injection, (b) frozen top-k ranker. The author states: "We do not propose a new memory system or rank policies."

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| errors (err/N) | FIFO 80k 124/336; 30k 243/336; 8k 299/336 | no-evict 95/336 | LongMemEval-S, top-k, GPT-4o-mini reader | seed 0, deterministic |
| errors | redundancy-aware 80k 127/336; 30k 242; 8k 300 | no-evict 95/336 | same | |
| errors | LLM-importance 80k 102/332; 30k 239; 8k 302 | no-evict 95/336 | same | N=332, not 336 (not explained in what I read) |
| errors | random 80k 387/1008; 30k 708; 8k 894 | no-evict 95/336 | pooled over 3 seeds | |
| two-bin irreversible share, 80k | FIFO 0.71 (CI .61–.81), random 0.73, redundancy 0.67, LLM-importance 0.60 (CI .47–.72), control 1.00 | no-evict 0.00 by construction | top-k regime | text and Table 1 agree |
| irreversible rate irr/N | FIFO 0.16/0.59/0.78; LLM-importance 0.10/0.59/0.80; control 8k 0.88 | no-evict 0.00 | 80k/30k/8k | |
| accuracy at 80k | LLM-importance "0.69 vs ≈0.62" for baselines | | text, §5.3 | beyond 0.05 caliper, so not counted as matched |
| matched-accuracy test resolution | "1.2–6 percentage points" | | n≈329 shared qids per pair | H2 amended after freeze |
| cost / latency | not stated | | | |

Derived (inference): no-evict accuracy ≈ (336-95)/336 = 0.72 on the oracle-answerable set; FIFO at 80k ≈ 0.63.

## Mechanism details you could implement
- Store cap in tokens; evict units by FIFO, random, redundancy-aware, or an LLM 1 to 10 importance score assigned without seeing the question.
- Restore audit: for each wrong answer, re-inject gold evidence, rerun reader at temperature 0, record correctness flip and whether gold survived eviction. Report irreversible/recoverable/residual.
- Pair per question; the paper notes "judge variance is on the order of the effect size, so pairing is mandatory."
- Include a deliberately destructive policy as positive control.

## Limitations, caveats, counter-evidence
- Reader and judge are the same model (GPT-4o-mini); GPT-5.4-mini used only as robustness reader.
- One benchmark, conversational QA; abstention questions excluded.
- LLM-importance is "a simple importance baseline rather than a state-of-the-art retention system."
- No summarising consolidation arm, no supersede or contradiction handling.
- H2 (matched-accuracy) was amended after the protocol freeze; the original "clean null" was an artifact of forced-gold.
- Residual errors dominated by cross-session aggregation (e.g. "$185" answered as "$65"); ≤20% may be judge-strictness cases.

## Takeaways for tuning a memory stack
- Evidence supports B6: every eviction policy at every binding budget had more errors than no-evict; forgetting here is pure loss.
- At tight budgets the loss is almost entirely irreversible, so better retrieval cannot compensate; retention capacity is what matters.
- Always report the retrieval regime with any budget-accuracy figure.
- The restore audit is cheap to bolt onto an existing eval harness (inference).

## Open questions
- Does the decomposition hold for coding-agent memory (file, decision, and error-log stores)?
- Would a summarise-before-evict policy move loss from irreversible to recoverable?
- Effect with a judge independent of the reader: not stated.
