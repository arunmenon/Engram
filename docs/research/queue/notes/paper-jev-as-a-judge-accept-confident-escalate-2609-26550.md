---
schema_version: 1
artifact_id: N-20260928-04
artifact_type: note
producer: triage
run_id: triage-20260928T014503Z-edff
created_at: 2026-09-28T01:55:04Z
input_refs: [{"artifact_id": "post:2104172198537855432", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.26550
claim_cluster: arxiv:2609.26550
feeds: ["decision", "memory"]
primary_source: https://arxiv.org/abs/2609.26550
source_commit: n/a
strength: paper-ablated
pillar_primary: R6
pillar_secondary: ["R4"]
tags: {"mechanism": ["decision model as judge", "confidence-threshold cascade", "temperature scaling"], "workload": ["preference judging", "factuality judging", "RewardBench", "JudgeBench", "HaluEval"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: judge accuracy against benchmark labels plus blinded human adjudication of disagreements", "control": "medium: sixteen comparators on identical items and a frozen cascade, but the threshold was fitted on a 96-item pilot and the multi-family expansion was exploratory, not pre-registered", "independence": "high: CMU authors funded by NIST and CMU AIMSEC; no vendor authorship stated", "reproducibility": "medium: reproducibility package in Appendix L without API credentials; one proprietary Jev version", "applicability": "medium: generic LLM-output judging, relevant to our eval harness and to decision-model gates"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["A confidence-threshold cascade (accept Jev at tau 0.9, escalate the rest to a frontier judge) held accuracy within 0.6 points of the frontier judge at 56.8% of its fee, escalating 53.7% of preference pairs; the frozen policy did not transfer consistently across fallback judges"]}
claim_correction: The post's "within 3 pts of a frontier judge at 0.36% of the fee" holds on ordinary preference and factuality (RewardBench -1.3, HaluEval +0.8), but on JudgeBench Jev trails GPT-6 by 14.6 points, and the 0.36% is the standalone fee; the cascade that keeps accuracy costs 56.8% of the fallback fee.
---

# JEV-as-a-Judge: Accept When Confident, Escalate When Unsure (arXiv 2609.26550)

- **URL:** https://arxiv.org/abs/2609.26550 (HTML https://arxiv.org/html/2609.26550)
- **Type:** paper
- **Author / org:** Yubo Li, Yidi Miao, Ramayya Krishnan, Rema Padman (Carnegie Mellon University); supported by NIST and CMU's AI Measurement Science and Engineering Center
- **Date:** submitted 2026-09-22
- **Retrieved:** 2026-09-28, arXiv abstract and HTML full text (v1)
- **Cited by evidence:** @rajeevchhajer, https://x.com/rajeevchhajer/status/2104172198537855432 ("JEV-as-a-Judge: a decision-only judge within 3 pts of a frontier judge at 0.36% of the fee. Escalate when unsure")
- **Relevance to a memory stack:** medium-high. Gives cost, accuracy, calibration and cascade numbers for using a decision model as a first-pass judge, the pattern we would use for eval scoring and for admission or supersession gates with escalation.

## TL;DR
- Jev compared with sixteen judges (thirteen hosted: GPT 4.1 mini through GPT-6 Astra, Qwen, Claude Sonnet 5, Gemini; plus local PairRM, Skywork-Reward-V2 and others) on RewardBench (400 pairs), JudgeBench (350), HaluEval (240), 150 multiple-choice replies with existing labels, RewardBench 2 (100 four-way), RM-Bench (80 style-adversarial pairs).
- vs the strongest comparator GPT-6: RewardBench 92.2 vs 93.5 (-1.3), HaluEval 87.5 vs 86.7 (+0.8), JudgeBench 78.6 vs 93.1 (-14.6). Larger gaps "when judgments require checking a derivation or resisting an elaborately written wrong answer".
- Cost and latency: "JEV's median latency is 0.152 seconds and its fee $0.044 per 1,000 judgments, against ... 1.885 seconds and $12.182 for GPT-6" (about 0.36%).
- Cascade at tau = 0.9 (fitted on a 96-item pilot): escalated 53.7% of preference pairs; accuracy 92.5% vs GPT-6 93.1% (-0.6); used 56.8% of the fallback's fee. "Frozen policies showed inconsistent transfer across different fallback models."
- Calibration: Brier 0.104 to 0.245 across tasks; error-detection AUROC 0.869 (RewardBench), 0.745 (JudgeBench), 0.863 (HaluEval); temperature scaling needs task-specific fitting.

## What it claims / describes
A decision-only judge as an economical first pass, with a frozen cascade that accepts confident verdicts and escalates uncertain ones to a stronger judge. Human check: one team member blindly adjudicated 183 disagreement items on RewardBench and HaluEval; after adjudication GPT-6 kept roughly a 2 to 3 point advantage on preference and factuality. Authors note "unknown training overlap and benchmark contamination" and that the multi-family expansion followed initial results, making it exploratory.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| accuracy RewardBench | 92.2% | GPT-6 93.5% | 400 pairs | |
| accuracy HaluEval | 87.5% | GPT-6 86.7% | 240 judgments | |
| accuracy JudgeBench | 78.6% | GPT-6 93.1% | 350 pairs | reasoning-heavy; big gap |
| human-adjudicated gap | GPT-6 ahead by about 2 to 3 points | | 183 adjudicated disagreements | one adjudicator |
| median latency | 0.152 s | GPT-6 1.885 s | | |
| fee per 1,000 judgments | $0.044 | GPT-6 $12.182 | | about 0.36% |
| cascade escalation rate | 53.7% | | preference pairs, tau 0.9 | threshold from 96-item pilot |
| cascade accuracy | 92.5% | GPT-6 93.1% | | -0.6 points |
| cascade cost | 56.8% of fallback fee | 100% | | |
| Brier score | 0.104 to 0.245 | | across tasks | |
| error-detection AUROC | 0.869 / 0.745 / 0.863 | | RewardBench / JudgeBench / HaluEval | |

## Mechanism details you could implement
- Cascade rule: accept the decision model's verdict if max probability >= tau (0.9 here), else escalate to the stronger judge. Fit tau on a held-out pilot to maximise coverage subject to staying within 2 points of the fallback's accuracy. Re-fit tau per fallback judge and per task: the frozen policy did not transfer.
- Temperature scaling per task before using probabilities as thresholds.

## Limitations, caveats, counter-evidence
- One proprietary Jev version; unknown contamination; exploratory expansion (authors).
- Threshold fitted on 96 items; escalation of more than half the items means the saving is about 43%, not 99.6%.
- Counter-evidence: Rao and Callison-Burch (arXiv 2609.29769, N-20260928-03) find cheap and flash LLM judges share 96% of Jev's most confident errors and that cascades gain at most 1.5 points over the best single judge. Confidence-based escalation cannot catch confident errors (inference drawn from both).

## Takeaways for tuning a memory stack
- A decision-model judge is fine for plain preference or grounded factuality first passes; do not use it alone where the judgment needs derivation checking.
- Budget cascades by escalation rate, which can exceed 50%.
- Per-task calibration is mandatory (supports B14).

## Open questions
- Escalation rates and accuracy on memory-specific judgments (is this served memory relevant, stale, contradicted).
- Cascade transfer across fallback judges: why inconsistent?

## Grading and labels
- Directness high; control medium (pilot-fitted threshold, exploratory expansion); independence high; reproducibility medium; applicability medium.
- Pillars: R6 primary (judge design, cost-aware evaluation), R4 secondary (confidence-gated escalation). Tags: cost.
- Beliefs: supports B14 (calibration must be fit per task; temperature scaling does not transfer). Would create a belief on cascade economics (about 57% of fee for -0.6 points). No contradiction with a held belief. Relation to the bus: complements vendor-langchain-jev-as-a-judge-agent-evals.md (N-20260926-10) and blog-neosigma-verifying-agent-traces-jev-judge.md (N-20260927-05) with an independent academic measurement.

## Origin chain
post 2104172198537855432 (@rajeevchhajer) -> arXiv 2609.26550 abstract and HTML -> benchmark, cost, cascade and calibration sections -> this note. Note for the checkpoint: two not-yet-due parked clusters (x:2104062773827113109, image-only HuggingPapers post about "JEV-as-a-Judge (Carnegie Mellon ...)", and possibly x:2103368968014848400) appear to concern this same paper; left untouched in pending per the not-yet-due rule, flagged in the triage log.
