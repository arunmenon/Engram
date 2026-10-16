---
schema_version: 1
artifact_id: N-20260927-10
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103846575948915068", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:nvlabs/skill2env
claim_cluster: github:nvlabs/skill2env
feeds: ["decision"]
primary_source: https://github.com/NVlabs/Skill2Env/blob/main/paper/Skill2Env_arXiv.pdf
source_commit: 9beb0b64a70290f862c8374bbef21f2ac88992ab
strength: paper-single-benchmark
pillar_primary: R5
pillar_secondary: ["R6"]
tags: {"mechanism": ["skills compiled into RL environments", "oracle/NOP task acceptance", "outcome-only RL (DPPO)", "rubric-calibrated LLM-judge reward", "SFT on teacher trajectories"], "workload": ["Terminal-Bench 2.1", "S2EBench (79 hand-verified tasks)"], "lifecycle_stage": ["training"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: pass@1 tables before and after RL on held-out benchmarks", "control": "medium: outcome-only vs outcome+rubric vs SFT arms on the same base model; single training run per arm, 5 trials per task at eval", "independence": "low: NVIDIA builds the pipeline, the private benchmark and the training stack", "reproducibility": "medium: code, SkillHub and dataset released at the pinned commit; generation cost over $90k; training code linked", "applicability": "low to medium: trains weights; relevant to us for its judge-reward and teacher-SFT negative results, not as a memory mechanism"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["Adding a rubric LLM-judge term to an outcome reward lowered held-out pass rates (TB 2.1 50.1 vs 54.1) while raising judged alignment with the source skill"]}
claim_correction: none (49.4 to 54.1 on Terminal-Bench 2.1 and 33.4 to 37.7 on S2EBench match Table 1; the post's "7,971 tasks across 13 domains" matches Section 3.3; the post omits that the rubric-reward arm did worse on both benchmarks and that S2EBench has 79 tasks)
---

# Reinforcing Agents with Collective Skills (Skill2Env, NVIDIA)

- **URL:** https://github.com/NVlabs/Skill2Env (paper PDF at paper/Skill2Env_arXiv.pdf; dair.ai summary https://academy.dair.ai/papers/reinforcing-agents-with-collective-skills)
- **Type:** paper (tech report in repo)
- **Author / org:** Binfeng Xu, Jian Hu, Hao Zhang, Shaokun Zhang, Yifan Zhang, Michael Demoret, Jan Kautz, Yi Dong; NVIDIA
- **Date:** repo HEAD 2026-09-21
- **Retrieved:** 2026-09-27, commit `9beb0b64a70290f862c8374bbef21f2ac88992ab` (2026-09-21 09:35:11 +0000, "nit"); local copy repos/Skill2Env; read PDF pages 1 to 12.
- **Cited by evidence:** @techwith_ram https://x.com/techwith_ram/status/2103846575948915068
- **Relevance to a memory stack:** low to medium. Not a memory mechanism; relevant as evidence on judge-based rewards (R6) and on skills as a source of task distributions for evaluating procedural memory (R5).

## TL;DR
- Pipeline: 5k crawled public Agent Skills filtered to SkillHub (about 3.4k); a Codex planner decomposes each skill into workflows; a Codex creator builds a Harbor task (Dockerfile world, instruction, tests, Must-do / Must-avoid / Best-practice rubric, reference solution); the host accepts a task only if the reference solution scores full reward and a no-op agent scores zero. Result: 7,971 tasks, 13 domains; generation cost "over $90k".
- RL: Qwen3.8-27B, DPPO binary-KL variant, 300 steps, G=8, delta=0.05, batch 64. Outcome-only RL: Terminal-Bench 2.1 49.4 -> 54.1, S2EBench pass 33.4 -> 37.7, S2EBench score 56.6 -> 75.1 (pass@1 over 5 trials).
- Outcome + rubric (LLM judge GPT-6 Astra, lambda 0.2): 50.1 / 34.7 / 63.6, below outcome-only on all three, but judged more aligned with the source skill (73.0% vs 54.5% preferred over base).
- SFT on GLM-5.3 teacher trajectories hurt: Qwen3.8-27B TB 2.1 49.4 -> 45.8; Qwen3.5-4B collapsed (18.7 -> 3.4).

## What it claims / describes
- Task acceptance (Section 3.2.3): model-free host gate; static checks on layout and symlinks; reject Dockerfiles whose build context escapes `environment/` or copies privileged files; base images pinned to digests; Oracle must earn full reward on every metric; NOP must earn zero.
- Reward: `tests/test.sh` writes up to six named metrics in [0, 1], averaged into r_V (partial credit). Rubric condition: r = r_V + lambda * s/5 with s in [-5, 5] from the judge, lambda = 0.2.
- Fidelity: TF-IDF over SKILL.md retrieves the true source skill top-1 for 73.2% of tasks (top-10 94.6%); rubric alone 68.5% top-1.
- S2EBench: 79 hand-verified held-out tasks from SkillHub skills.
- Transfer check: training tasks share "no task above 13-gram Jaccard similarity of 0.8" with Terminal-Bench.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Terminal-Bench 2.1 pass@1 | 54.1 (outcome RL) | 49.4 base; 50.1 outcome+rubric | Table 1, 5 trials per task, Pi harness | one training run per arm |
| S2EBench pass@1 | 37.7 | 33.4 base; 34.7 rubric | Table 1, 79 tasks | authors' private benchmark |
| S2EBench mean score | 75.1 | 56.6 base; 63.6 rubric | Table 1 | |
| judge prefers RL trajectory | 54.5% (outcome RL) / 73.0% (rubric RL) | prefers base 33.5% / 24.0% | Table 2, 200 paired trajectories, judge sees SKILL.md | judge = same GPT-6 Astra as the reward judge |
| SFT on teacher (27B) | TB 45.8, S2E pass 33.9 | base 49.4 / 33.4 | Table 3 | |
| SFT on teacher (4B) | TB 3.4, S2E 0.0 | base 18.7 / 5.8 | Table 3 | collapse into loops |
| teacher rollouts | 15,968 trajectories, mean reward 0.74 | | GLM-5.3, Section 3.4 | |
| generation cost | over $90k | | GPT-5.6 Sol xhigh | released set regenerated with Kimi-K3-max |

## Mechanism details you could implement
- Task acceptance gate for any evaluation set we generate: reference solution must pass every metric, a no-op must fail every metric, no privileged files in the build context, pinned image digests.
- Keep a judge-based quality term small and separate from the outcome reward, and report both; here the judge term pulled against the outcome metric.
- Use practitioner-written skills (SKILL.md) as a source of realistic workflow tasks with a rubric carried over from the skill.

## Limitations, caveats, counter-evidence
- Authors do not read the rubric result as a verdict: lambda, additive form and a judge that sees messages but not the filesystem "were all fixed without tuning".
- Alignment preference uses the same judge model as the reward (shared-model judge, R6).
- One base model; single RL run per arm; private benchmark of 79 tasks built by the authors.
- Released dataset differs from the one trained on (regenerated with Kimi-K3-max "for legal reasons").

## Takeaways for tuning a memory stack
- If our outcome loop (H4/H6) scores episodes with an LLM judge, expect the judge term to trade against task success; keep it bounded and measured separately.
- Imitating a stronger agent's trajectories can hurt a weaker agent; relevant to "learn from another agent's traces" memory designs (inference).
- The Oracle/NOP acceptance rule is a cheap validity check for any held-out memory benchmark we build.

## Open questions
- Would a tuned lambda or a filesystem-aware judge reverse the rubric result?
- Variance across RL seeds?

## Grading and labels
- Directness high; control medium; independence low; reproducibility medium; applicability low to medium.
- Pillars: R5 primary (learning from experience, procedure sources, teacher transfer); R6 secondary (judge reward and shared-model judge).
- Would create: rubric-judge reward lowered held-out pass rates while raising judged alignment (one run).
- No belief contradicted. B16 (raw vs distilled) not tested.

## Origin chain
post 2103846575948915068 (@techwith_ram) -> github.com/NVlabs/Skill2Env at 9beb0b64 -> paper/Skill2Env_arXiv.pdf Sections 3.2 to 3.5, 4.2, Tables 1 to 3 -> this note. Independence: NVIDIA pipeline, benchmark and training stack (Molt, Polar) all from the same group.
