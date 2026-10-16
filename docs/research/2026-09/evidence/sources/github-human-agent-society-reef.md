---
schema_version: 1
artifact_id: N-20260927-12
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2094869008076181718", "file_id": null, "sha256": null}, {"artifact_id": "post:2094867930081337730", "file_id": null, "sha256": null}, {"artifact_id": "post:2103525687155908782", "file_id": null, "sha256": null}, {"artifact_id": "post:2102496199219556373", "file_id": null, "sha256": null}, {"artifact_id": "post:2100969299963682835", "file_id": null, "sha256": null}, {"artifact_id": "post:2094882573109616926", "file_id": null, "sha256": null}, {"artifact_id": "post:2095064336100368852", "file_id": null, "sha256": null}, {"artifact_id": "post:2102499451231175035", "file_id": null, "sha256": null}, {"artifact_id": "post:2103910534613815759", "file_id": null, "sha256": null}, {"artifact_id": "post:2103798054361198935", "file_id": null, "sha256": null}, {"artifact_id": "post:2095663808421503088", "file_id": null, "sha256": null}, {"artifact_id": "post:2094907865903648996", "file_id": null, "sha256": null}, {"artifact_id": "post:2098675209733644383", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:human-agent-society/reef
claim_cluster: github:human-agent-society/reef
feeds: ["memory"]
primary_source: https://github.com/Human-Agent-Society/reef
source_commit: 5de976be90c0676c60694e55499255a81913f8fd
strength: repo-pinned
pillar_primary: R5
pillar_secondary: ["R6", "R1"]
tags: {"mechanism": ["harness self-improvement (meta-harness)", "strict-improvement selection", "receipt-linked feedback", "versioned artifact publication"], "workload": ["Terminal-Bench 2 (30-task hard subset)"], "lifecycle_stage": ["promotion", "evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-iteration pass counts for Reef and the upstream implementation on the same tasks", "control": "medium: same tasks, models, runtime and seed harness for both arms; two repeats per measurement; no held-out tasks", "independence": "medium: reproduces an external method (stanford-iris-lab/meta-harness) against its own upstream code", "reproducibility": "high: pinned Reef commit, pinned task revision 69671fba, pinned upstream 44b99421, runtime versions listed", "applicability": "medium: harness self-improvement on terminal tasks; the finding that matters to us is the size of baseline noise"}
beliefs_affected: {"supports": ["B21"], "contradicts": [], "would_create": ["On a 30-task, 2-repeat Terminal-Bench measurement, the same vanilla harness scored 20/60 and 24/60 in two arms; the selected self-improvement gain (+3/60) was inside that spread and shrank to +1/60 on remeasurement"]}
claim_correction: posts describe Reef as infrastructure for agents to "continuously evolve"; its own Terminal-Bench meta-harness reproduction shows no gain beyond baseline noise (selected 23/60 vs its baseline 20/60, but the same vanilla baseline scored 24/60 in the upstream arm; fresh remeasurement 22/60 vs 21/60)
---

# Reef: infrastructure for continually self-improving agents (Human-Agent-Society/reef)

- **URL:** https://github.com/Human-Agent-Society/reef
- **Type:** repo
- **Author / org:** Human-Agent-Society (posts by @ao_qu18465, @hanzheng_7); PyPI `reef-infra`
- **Date:** open-sourced 2026-09-01; `/reefine` announced 2026-09-25
- **Retrieved:** 2026-09-27, commit `5de976be90c0676c60694e55499255a81913f8fd` (2026-09-27 09:39:07 +0800, "Update header for clarity in README.md (#654)"); local copy repos/reef. Read: README.md, recipes/meta_harness/examples/terminal_bench/README.md, recipes/meta_harness/RESULTS.md.
- **Cited by evidence:** @ao_qu18465 https://x.com/ao_qu18465/status/2094869008076181718 , https://x.com/ao_qu18465/status/2094867930081337730 , https://x.com/ao_qu18465/status/2103525687155908782 and replies/quotes listed in input_refs
- **Relevance to a memory stack:** medium. The infrastructure (receipt-linked feedback, versioned publication, rejected candidates leave the release serving) is close to our gated-update design, and its own reproduction is a clean, pinned measurement of how large baseline noise is relative to self-improvement gains.

## TL;DR
- Reef connects inference, feedback, learning and versioned delivery; it can evolve weights (Slime, SGLang) or the harness (prompts, rules, skills). Recipes: SAO, GEPA, Meta-Harness, TTT-Discover, OpenClaw-RL, SkillClaw, Reefine.
- Meta-Harness reproduction on a 30-task hard Terminal-Bench 2 subset, 2 repeats (60 trials) per measurement, target gpt-5.6-luna, proposer gpt-5.6-sol, xhigh:
  - Reef arm: baseline 20/60, iterations 23, 20, 20, 23; selects iteration 1 (23/60).
  - Upstream arm: baseline 24/60, iterations 22, 20, 21, 21; keeps baseline (24/60).
  - Fresh remeasurement of the selected harnesses: Reef iteration 1 22/60 (36.67%) vs upstream baseline 21/60 (35.00%).
- The same vanilla Terminus 2 baseline scored 20/60 and 24/60: a 4-trial spread that exceeds Reef's selected gain (+3), which shrank to +1 on remeasurement.
- Selector check: replaying the same score histories through Reef's selector and upstream's `update_frontier` gave identical choices on all eight decisions.

## What it claims / describes
- Loop (README figure): "Reef serves requests, records feedback, produces updates, and commits accepted updates to a version history." Commit stage: "Apply the configured selection policy and publish accepted updates" with candidate evaluation, version history and artifact delivery modules. "Rejected candidates leave the current release serving."
- Harness optimisation needs "A model endpoint, representative tasks, and an evaluator; no local training GPUs".
- Meta-Harness setting: selection = strict improvement in mean score; ties keep the current choice; baseline plus four full-history iterations per arm.
- Scope statement (RESULTS.md): "This is a method reproduction on 30 tasks, with shared API, sandbox, and verifier"; the remeasurement "did not feed back into search and are not a held-out task evaluation".

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| vanilla baseline, Reef arm | 20/60 | upstream arm same harness 24/60 | 30 tasks x 2 repeats | same harness measured twice |
| best selected, Reef | 23/60 (iteration 1) | 20/60 | strict-improvement rule | gain 3/60 |
| best selected, upstream | 24/60 (baseline kept) | | | no iteration beat baseline |
| remeasurement | Reef iter 1 22/60 (36.67%) | upstream baseline 21/60 (35.00%) | two fresh repeats, same tasks | not held-out; one infra loss per arm replaced |
| selector agreement | 8/8 identical decisions | upstream update_frontier | replayed histories | checks rule, not proposals |

## Mechanism details you could implement
- Strict-improvement promotion with ties keeping the incumbent, and a versioned history where rejected candidates never replace the serving release.
- Separate selection measurement from confirmation remeasurement, and report both.
- (inference) Before accepting any self-improvement or memory update on a small task set, measure the unchanged baseline at least twice and require the gain to exceed that spread (the synthesis's noise-floor rule, section 6).

## Limitations, caveats, counter-evidence
- 30 tasks, 2 repeats; no held-out evaluation; one infrastructure loss per arm replaced.
- Other recipe results (AIME, IMOAnswerBench, CEO-Bench, WildClawBench, TriMul) not read this run.
- The `/reefine` claims in the posts ("120 papers screened in 9 s") are anecdotes without a results page.

## Takeaways for tuning a memory stack
- On benchmarks of this size, a 4-in-60 swing is noise; any memory or harness change claiming a few points on 30 tasks needs repeated baselines.
- Reef's commit stage (evaluate candidate, publish only accepted updates, keep version history) is a usable reference for our gated-update pipeline; add the scope condition from N-20260927-02.

## Open questions
- Results with held-out tasks and more repeats?
- Do the other recipes' result pages report baseline repeats?

## Grading and labels
- Directness high; control medium; independence medium; reproducibility high; applicability medium.
- Pillars: R5 primary (harness self-improvement infrastructure); R6 secondary (noise floor, reproduction); R1 secondary (receipt-linked feedback, versioned artifacts).
- B21 supports: small n bounds what can be concluded.
- Would create: baseline spread (20 vs 24 of 60) exceeded the selected gain.
- No contradiction rows. Consistent with synthesis section 6 noise-floor advice.

## Origin chain
posts @ao_qu18465 (2094867930081337730 launch, 2094869008076181718, 2103525687155908782 reefine) and quotes -> github.com/Human-Agent-Society/reef at 5de976be -> recipes/meta_harness/examples/terminal_bench/README.md Results; recipes/meta_harness/RESULTS.md iteration table and scope -> this note. Independence: reproduction of stanford-iris-lab/meta-harness at 44b99421; not affiliated with RRSI or EvoSkill sources.
