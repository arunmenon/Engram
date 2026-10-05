---
schema_version: 1
artifact_id: N-SURVEY-20261001-07
artifact_type: note
producer: triage
run_id: survey-20261001T054505Z-09ae
created_at: 2026-10-01T06:22:00Z
idempotency_key: note:survey:arxiv:2609.39111
input_refs: []
pillar_primary: R9
pillar_secondary: [R4]
memory_stage: none
priority: 2
beliefs_affected:
  supports: []
  contradicts: []
related_notes: [N-20260929-09, N-20260928-14, N-SURVEY-20261001-04, N-SURVEY-20261001-06]
evidence:
  directness: 3
  control: 3
  independence: 2
  reproducibility: 3
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.39111
secondary_sources:
  - https://huggingface.co/AgentBull/bongard-mini
  - https://huggingface.co/Mapika/decider-2b
  - https://arxiv.org/abs/2609.36965
found_via: survey
claim_cluster: open-weight-system-one-roster-2026-10-01
---

# Open-weight System One roster update, 2026-10-01: Bongard (arXiv 2609.39111), decider-2b, Chinese-Jev (arXiv 2609.36965), KEV

- **URL:** https://arxiv.org/abs/2609.39111 (read: html v1); weights https://huggingface.co/AgentBull/bongard-mini (Hugging Face API record read); runtime https://github.com/AgentBull/bongard. Companions read: https://huggingface.co/Mapika/decider-2b (model card); https://arxiv.org/abs/2609.36965 (html v1), project page https://gulucaptain.github.io/Chinese-Jev/
- **Type:** paper plus model cards (vendor self-reports)
- **Author / org:** Bongard: Li Ding, Haidi Jin, Chen Ji (AgentBull). decider-2b: Mapika. Chinese-Jev: Zexiao Wang, Shuicheng Yan and others (Fudan University, National University of Singapore, UCAS)
- **Date:** Bongard 2026-09-30 (weights created 2026-09-27); decider-2b 2026-09-24; Chinese-Jev 2026-09-29
- **Retrieved:** 2026-10-01
- **Cited by evidence:** survey run, R9 plan question 1 (roster) and question 3 (how much own data a fine-tune needs)
- **Relevance to a memory stack:** high for priority 2. These are new candidates for a self-hosted decision model, each with a stated head-to-head against Jev; all numbers are the makers' own.

## TL;DR
- **Bongard (bongard-mini)**: T5Gemma 2 4B-4B encoder-decoder, 7.51B parameters, Gemma terms of use (runtime Apache 2.0). One encoder pass serves many questions: 36 ms median for a short request, 32 questions about one state in 221 ms on one RTX PRO 6000; runs on an RTX 4090. On DecisionBench 1.0 (23,900 decisions, maintained by Hanno Labs): 78.05%, 4th of 61, ECE 0.063, vs Jev 1.13 at 72.0%, ECE 0.128. On 49,291 items from 24 public benchmarks it led Jev on 6; Jev still leads on typed-decisions teacher agreement and several subjective benchmarks.
- **decider-2b (v11)**: Qwen3.5-2B-Base fine-tune, Apache 2.0, 3.8 GB BF16 (FP8 available), 3.2 ms per request, about 2,700 decisions/s at batch 32. On JevBench vs Jev 1.13.0: hard 0.577 vs 0.730, standard 0.889 vs 0.986, easy 1.000 vs 1.000. It trails Jev clearly.
- **Chinese-Jev**: mmBERT-base encoder plus decision head, about 322M parameters, CC BY 4.0 announced but weights "will" be released (not yet). 14 ms per decision locally (20.3x faster than the Jev API, network included). General Chinese tasks 69.20% vs Jev 68.35%, ECE 3.78% vs 11.45%.
- **Fine-tune data size (Chinese-Jev)**: the medical specialist trained on 3,000,000 decisions beat Jev (87.65% vs 84.29%); the legal and finance specialists trained on 24,000 decisions each lost (60.10% vs 68.35%; 64.72% vs 78.39%), and legal ECE rose from 15.37% to 17.45% after specialisation. 24,000 in-domain labels on a 322M encoder were not enough to beat Jev.
- **KEV-0.8B / 4B / 9B** (Qwen3.5-based, seen in N-SURVEY-20261001-06): open family measured by a third party. Average ordinal scale use was slightly below Jev (65% to 70% vs 73%), but on a 14-level scale KEV-4B and KEV-9B used more levels than Jev (68.4% and 74.9% vs 54.5%).

## Roster table (additions this run)

| Model | Size | Licence | Hardware / latency | Published quality vs Jev | Maintainer | Independent check? |
|---|---|---|---|---|---|---|
| Bongard (bongard-mini) | 7.51B (T5Gemma 2 4B-4B) | Gemma terms; runtime Apache 2.0 | RTX PRO 6000 or RTX 4090; 36 ms short request; 32 questions per state 221 ms; 400,000 decisions per hour per GPU | DecisionBench 78.05% vs Jev 72.0%; ECE 0.063 vs 0.128; typed-decisions KL 0.256 vs 1.442, Brier 0.132 vs 0.148; Banking77 93.1% vs 79.8%; PAWS 91.1% vs 84.9% | AgentBull | no |
| decider-2b v11 | 2B (Qwen3.5-2B-Base) | Apache 2.0 | 3.2 ms single request (CUDA graphs); 3.8 GB BF16 | JevBench hard 0.577 vs 0.730; standard 0.889 vs 0.986 | Mapika | no |
| Chinese-Jev | about 322M (mmBERT-base) | CC BY 4.0 announced; weights not yet released | 14 ms per decision; about 1 s INT8 on iPhone 15 Pro | Chinese general 69.20% vs 68.35% | Fudan / NUS / UCAS authors | no |
| KEV-0.8B, 4B, 9B | 0.8B to 9B (Qwen3.5) | not stated | not stated | 14-level scale use: KEV-9B 74.9%, KEV-4B 68.4%, KEV-0.8B 26.5% vs Jev 54.5%; no accuracy head-to-head captured | Jared Palmer (per arXiv 2609.38827) | yes, third-party (arXiv 2609.38827) |

## Numbers (Bongard ablations and DecisionBench)

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| DecisionBench accuracy | 78.05% (rank 4 of 61) | Imajev-4B 79.7%; Winnow-12B 76.7%; Jev 1.13 72.0% | 23,900 decisions | benchmark maintainer Hanno Labs; leaderboard not fetched this run |
| ECE / NLL | 0.063 / 0.72 | Jev 0.128 / 2.43; Imajev-4B 0.069 / 0.69 | same | |
| Stage 2 (joint-embedding) held-out rephrasings | 75.7% to 85.9% | | | "short independent control" only |
| Stage 3 sandbox panel | 50.6% to 64.8% | | own environments | not tested on unseen environments |
| Fair-chance questions, mean KL from uniform | 0.0009 | Jev 0.769 | | |
| Long documents | all 260 requests correct at every length up to 30,000 tokens | | | |

## Mechanism details you could implement
- Bongard's "read once, ask many" design suits memory stages that ask several questions about the same retrieved state (relevant? stale? contradicts? which requirement?). 32 questions in 221 ms makes per-memory multi-question gates affordable on one GPU.
- For a quick self-hosted baseline, decider-2b runs on very small hardware but trails Jev on hard items; expect to fine-tune.
- From Chinese-Jev: plan on far more than 24,000 labelled decisions to beat a hosted model from a 322M encoder in a narrow domain, or start from a larger base.

## Limitations, caveats, counter-evidence
- Every head-to-head in this note is a vendor self-report; no independent replication found. DecisionBench and its maintainer were not verified this run (a web search did not surface the leaderboard).
- Bongard's answers "change when other instructions join the request" (question-aware encoding), a consistency risk for multi-question gates.
- Bongard's Gemma licence carries use restrictions; check before production use.
- No page content addressed instructions to an AI agent.

## Takeaways for tuning a memory stack
- Shortlist for an in-house comparison against Jev on our own memory decisions: Bongard (strongest published numbers, needs one large consumer or workstation GPU) and an Apache-2.0 small model (decider-2b, or od1 from N-20260928-14) as the cheap floor. The existing self-hosting cards (PC-20260929-04, PC-20260928-10) already define that test; this note adds candidates, not a new test.
- Budget labels: a narrow-domain fine-tune with tens of thousands of labels did not beat Jev in Chinese-Jev's legal and finance runs.

## Open questions
- Does DecisionBench publish per-item data and Jev's row independently?
- Do Bongard's 32-questions-per-state answers stay stable when the question set changes?
