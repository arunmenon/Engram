---
schema_version: 1
artifact_id: N-20261010-03
artifact_type: note
producer: triage
run_id: triage-20261010T014501Z-4cec
created_at: 2026-10-10T01:54:06Z
input_refs: [{"artifact_id": "post:2103754592056144155", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2608.05628
claim_cluster: arxiv:2608.05628
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2608.05628
source_commit: n/a
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R6"]
memory_stage: consolidation
tags: {"mechanism": ["skill-revision-tree", "hypothesis-self-verification", "replay-on-cached-outputs"], "workload": ["agent-skills", "skillsbench"], "lifecycle_stage": ["learn"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: Table 1 and Table 2 report pass rates per arm", "control": "high: baselines incl. CoEvoSkills and human skills, two ablations, 3 seeds, token accounting", "independence": "medium: authors' own method; official SkillsBench verifier is external", "reproducibility": "low: no code or data link found on the HTML page", "applicability": "medium: procedural memory for agents; tasks are not our engineering workload"}
beliefs_affected: {"supports": ["B15"], "contradicts": [], "would_create": ["Keeping prior skill versions as a tree and choosing among them on replayed evidence beats in-place skill refinement"]}
claim_correction: none
---

# SkillHEX: Improving Agent Skills via Hypothesis-Driven Autonomous Exploration and Exploitation (arXiv 2608.05628)

- **URL:** https://arxiv.org/abs/2608.05628 (HTML read: https://arxiv.org/html/2608.05628)
- **Type:** paper
- **Author / org:** Yuru Feng, Yaoqi Chen, Beidi Zhao, Qianxi Zhang, Xinjiang Wang, Jianan Lu, Zhirui Wang, Shusen Xu, Zengzhong Li, Qi Chen; Microsoft, UC San Diego, USTC, UBC
- **Date:** v1 submitted 2026-08-06
- **Retrieved:** 2026-10-10, v1
- **Cited by evidence:** https://x.com/DerekHJH9/status/2103754592056144155 (@DerekHJH9, Awesome RSI)
- **Relevance to a memory stack:** medium. Procedural memory (skills) that is revised from failures; the ablations isolate two design choices we would face: verify the diagnosis before revising, and keep old versions instead of overwriting.

## TL;DR
- On 87 SkillsBench tasks with 1 initial evaluation plus up to 5 evolved attempts, SkillHEX reaches 55.9 +/- 1.8 (GPT-5.3-Codex) and 57.9 +/- 2.4 (Claude Opus 4.7), vs CoEvoSkills 46.4 and 49.4 and human-written skills 52.9 and 54.4 (Table 1, 3 seeds).
- Ablations (Table 2, GPT-5.3-Codex): without the self-verifier 44.8 (-11.1 pp); without the skill patch tree (in-place refinement) 49.1 (-6.8 pp).
- 18.0% fewer total tokens per task than CoEvoSkills (2356.1K vs 2874.3K, Table 3).

## What it claims / describes
After a failed execution, a reflection module proposes falsifiable hypotheses about the cause; a self-verification module writes executable tests for them; tests are replayed on cached historical outputs to update evidence per skill version; refuted hypotheses and their tests are removed. Candidate revisions are generated from this evidence; search picks the next attempt by diagnostic scores, rankings and visit counts, and can revisit retained branches. Each execution starts fresh with only the selected skill injected; "the official verifier returns only pass or fail", and verifier details are hidden from all LLMs.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| pass rate, GPT-5.3-Codex | 55.9 +/- 1.8 | CoEvoSkills 46.4 +/- 0.7; No Skill 33.3 +/- 4.1; Human 52.9 +/- 5.0 | SkillsBench 87 tasks, Table 1, 3 seeds | mean +/- std, no CI |
| pass rate, Claude Opus 4.7 | 57.9 +/- 2.4 | CoEvoSkills 49.4 +/- 5.0; Human 54.4 +/- 1.3 | same | |
| w/o self-verifier | 44.8 +/- 2.0 | full 55.9 | Table 2, GPT-5.3-Codex | |
| w/o skill patch tree | 49.1 +/- 1.3 | full 55.9 | Table 2 | in-place refinement |
| total tokens per task | 2356.1K | CoEvoSkills 2874.3K | Table 3 | |

## Mechanism details you could implement
- Store procedure revisions as a tree with per-version evidence; never overwrite.
- Before accepting a diagnosis, turn it into an executable test and replay it on cached past outputs.
- Allocate attempts by evidence score plus visit count (bandit-style).

## Limitations, caveats, counter-evidence
- Revisions happen between attempts on the same test task (online, per-task); transfer to new tasks is not shown in what we read.
- No limitations section and no code link in the HTML we read.
- Std over 3 seeds is wide for some baselines (CoEvoSkills Opus +/- 5.0).

## Takeaways for tuning a memory stack
- If we store learned procedures, keep versions and evidence (supersede, do not modify), consistent with "prefer add over modify" (B3 spirit, inference).
- Validating a lesson against replayed history before promoting it is worth about 11 pp here.

## Open questions
- Cross-task transfer; harmful reinforcement rate (B17).
- Release of code and per-task results.

## Grading and labels
- Directness high, control high, independence medium, reproducibility low, applicability medium.
- Pillar R5, secondary R6. Stage: consolidation. No priority match.
- B15 supports: evidence across retained branches beats single-line refinement (49.1 vs 55.9).
- Would create: version tree beats in-place skill update.

## Origin chain
post 2103754592056144155 (@DerekHJH9) -> arXiv 2608.05628 HTML, Tables 1 to 3 -> this note. Independence: no shared authors with other noted skill-evolution sources known to us.
