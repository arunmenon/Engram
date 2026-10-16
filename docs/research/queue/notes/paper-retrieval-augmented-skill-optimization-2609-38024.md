---
schema_version: 1
artifact_id: N-20261001-08
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105252472369684592", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.38024
claim_cluster: arxiv:2609.38024
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.38024
source_commit: n/a
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R3"]
tags: {"mechanism": ["skill retrieval from external corpus", "cross-harness adaptation", "failure-driven skill update", "validation-gated acceptance", "leakage blocklist"], "workload": ["office documents", "spreadsheets", "embodied text games", "web shopping"], "lifecycle_stage": ["retrieval", "consolidation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: full baseline table with standard errors and component ablations", "control": "high: three seeds, matched rollout budgets with TextGrad and WikiSkill, ablation of adaptation and of each stage", "independence": "medium: one group; GitSkills corpus size not disclosed", "reproducibility": "medium: seeds and splits stated; code and corpus availability not checked", "applicability": "medium: skill or procedure memory for agents, not engineering artifacts specifically"}
beliefs_affected: {"supports": ["B16"], "contradicts": [], "would_create": ["Skills retrieved from an external corpus help only after they are adapted to the target harness; raw retrieved skills can do worse than no skill (ALFWorld 55.97 vs 64.43)"]}
claim_correction: none (the post's numbers match Table 1: SpreadsheetBench 63.33 vs SkillOpt 57.02, OfficeQA 49.03 vs 45.54, ALFWorld 74.13 vs 72.64; RASI 45.74 vs RFSI 40.11 on OfficeQA)
memory_stage: retrieval
---

# Retrieval-Augmented Skill Optimization via Cross-Harness Adaptation (RASO, arXiv 2609.38024)

- **URL:** https://arxiv.org/abs/2609.38024 (HTML: https://arxiv.org/html/2609.38024)
- **Type:** paper
- **Author / org:** Jaewon Chu, Ji Soo Lee, Jihwan Park, Dohwan Ko, Jeehye Na, Seunghun Lee, Taehoon Lee, Minseo Yoon, Minseok Joo, Yunyang Xiong, Hyunwoo J. Kim (affiliations not shown on abstract page)
- **Date:** submitted 2026-09-29
- **Retrieved:** 2026-10-01 (abstract and HTML: method, Tables 1, 2, 3, 5, 9, 10, leakage section)
- **Cited by evidence:** @runbywren, 2026-09-30, https://x.com/runbywren/status/2105252472369684592
- **Relevance to a memory stack:** medium. It measures procedural memory imported from outside (other teams' skills) and shows the adaptation step, not the retrieval, carries the value; raw retrieved procedures can hurt.

## TL;DR
- RASI (initialisation, zero rollouts): generate procedure queries from the task and harness descriptions, BM25-retrieve top K=5 sections per query from the GitSkills corpus, adapt them to the target harness, synthesise a skill. RASU (update): from failed trajectories, generate textual gradients and queries, retrieve and adapt again, update, and accept only if validation improves.
- Cross-Harness Adaptation rules: "(1) remove domain-specific nouns and omit procedures without counterparts in the target harness, (2) focus exclusively on requirement, (3) preserve specific claims about tool or parameter behavior only when corroborated by target harness description."
- GPT-5.6-Luna, RASO vs best update baseline: OfficeQA 49.03 vs 45.54 (SkillOpt); SpreadsheetBench 63.33 vs 57.02 (SkillOpt); ALFWorld 74.13 vs 72.64 (SkillOpt); WebShop 46.61 vs 45.54 (GEPA). Three seeds, mean +/- s.e.
- Raw retrieval without adaptation (SkillRouter) is worse than no skill on ALFWorld (55.97 vs 64.43, GPT) and WebShop (Qwen 9.42 vs 16.27). Removing adaptation costs RASI 3.88 / 7.74 points (OfficeQA / SpreadsheetBench).
- Leakage control: "We construct a per-benchmark blocklist and remove it from the corpus before building the retrieval index", with repository-level exclusion.

## What it claims / describes
Two-stage skill optimisation for a frozen agent model. Initialisation baselines: No Skill, SkillRouter (direct retrieval), RFSI (retrieval-free LLM-generated skill). Update baselines: TextGrad, GEPA, SkillOpt, WikiSkill. Optimisation: 2 epochs over the training split, minibatch of 40 tasks, validation-gated acceptance (keep the previous skill if no improvement). Rollouts matched with TextGrad and WikiSkill (196, 320, 114, 360 across the four benchmarks). Splits (Table 5): OfficeQA 50/24/172; SpreadsheetBench 80/40/280; ALFWorld 39/18/134; WebShop 80/40/500 (train/val/test).

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| OfficeQA, GPT-5.6-Luna, RASO | 49.03 +/- 1.85 | SkillOpt 45.54 +/- 2.05; GEPA 43.99; TextGrad 43.80; No skill 11.44 | 172 test, 3 seeds, Table 1 | |
| SpreadsheetBench, GPT | 63.33 +/- 2.69 | SkillOpt 57.02 +/- 3.60; GEPA 54.53; No skill 32.98 | 280 test | |
| ALFWorld, GPT | 74.13 +/- 1.00 | SkillOpt 72.64 +/- 0.90; No skill 64.43; SkillRouter 55.97 | 134 test | small margin |
| WebShop, GPT | 46.61 +/- 0.11 | GEPA 45.54 +/- 0.35; No skill 43.56 | 500 test | small margin |
| OfficeQA / SS / ALF / Web, Qwen-3.5-9B, RASO | 42.25 / 31.55 / 51.00 / 24.73 | best other update baseline 37.40 / 29.76 / 43.53 / 13.43 | Table 1 | |
| RASI (init only, 0 rollouts), GPT, OfficeQA | 45.74 +/- 1.40 | RFSI 40.11 +/- 0.58 | Table 1 | |
| stage ablation, GPT, OfficeQA / SS | RFSI+RFSU 40.70/51.67; RFSI+RASU 47.56/61.07; RASI+RFSU 45.93/58.45; RASI+RASU 49.03/63.33 | | Table 2 | |
| adaptation ablation, RASI | without 41.86/41.43 -> with 45.74/49.17 | | Table 3 | |
| adaptation ablation, RASU | without 46.70/57.86 -> with 49.03/63.33 | | Table 3 | |
| API cost, WebShop | $10.28 | TextGrad $41.03 | Table 9 | lowest on 3 of 4 benchmarks |

## Mechanism details you could implement
- Section-level BM25 retrieval over a corpus of procedures (not whole documents), K=5 sections per query; gains plateau beyond K=5.
- Adapt before use: strip domain nouns, drop steps the target environment cannot perform, keep tool or parameter claims only if the target's own documentation corroborates them.
- Failure-driven update: from failed trajectories, write a textual gradient, retrieve against it, adapt, and accept the new skill only if validation improves.
- Leakage hygiene: a per-benchmark blocklist (benchmark names, dataset identifiers) removed from the corpus at repository level before indexing.

## Limitations, caveats, counter-evidence
- No dedicated limitations section; corpus size not disclosed; adaptation agent model not named in the extraction.
- WebShop and ALFWorld margins over the best baseline are about 1 to 1.5 points.
- Skills are compared against other skill-optimisation methods, not against raw trajectories as memory (B16's comparison is not run).

## Takeaways for tuning a memory stack
- Importing procedures from other teams or repositories needs an adaptation step grounded in the target's own docs; unadapted retrieval can be worse than nothing.
- Validation-gated acceptance (keep the old skill unless the new one wins on validation) is a cheap write gate for procedural memory; it matches the EvoSkill pattern in our synthesis.
- Copy the blocklist approach for our PDLC benchmark corpus.

## Open questions
- Does adapted retrieval beat raw episode records (SelfSearch-style, N-20261001-06) as the procedural memory?
- What fraction of retrieved sections survive adaptation, and how often does adaptation introduce wrong tool claims?

## Grading and labels
- **Directness: high.** **Control: high.** **Independence: medium.** **Reproducibility: medium.** **Applicability: medium.**
- **Pillars:** R5 primary (procedure induction and transfer); R3 secondary (retrieval of procedures). **Memory stage:** retrieval.
- **Beliefs:** supports B16's caution that induced or imported procedures are a hypothesis: unadapted retrieved skills hurt (SkillRouter below No skill on ALFWorld), adapted ones help. **Contradictions:** none.

## Origin chain
Post @runbywren 2105252472369684592 (2026-09-30) -> arXiv 2609.38024 -> Table 1 (all baselines), Tables 2 and 3 (ablations), Table 5 (splits), Tables 9 and 10 (cost, rollouts), leakage paragraph -> this note. Independence: baselines from other groups (TextGrad, GEPA, SkillOpt, WikiSkill); same benchmark family (OfficeQA) as EvoSkill in our catalogue.
