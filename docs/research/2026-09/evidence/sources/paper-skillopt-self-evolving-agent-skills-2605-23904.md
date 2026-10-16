---
schema_version: 1
artifact_id: N-20260926-01
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103783560029020597", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2605.23904
claim_cluster: arxiv:2605.23904
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2605.23904
source_commit: 79124b37e9a6371e13b753f8bcd7adb1e493ade1
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R6"]
tags: {"mechanism": ["skill induction", "validation-gated edits", "text-space optimizer", "rejected-edit buffer"], "workload": ["search QA", "spreadsheet", "office docs", "math", "embodied text game"], "lifecycle_stage": ["write", "promotion"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: the paper reports held-out test scores for the optimized skills", "control": "medium: strong baselines (no skill, human skill, GEPA, EvoSkill, TextGrad, Trace2Skill) and ablations, but no raw-trajectory arm and single runs", "independence": "low: all numbers from the Microsoft authors; no external replication found", "reproducibility": "medium: MIT repo at a pinned commit and deterministic split seed 42, but no seeds-over-runs or intervals", "applicability": "medium: office and spreadsheet tasks are closer to engineering work than chat memory; no coding-agent benchmark"}
beliefs_affected: {"supports": ["B17"], "contradicts": ["B16"], "would_create": ["Validation-gated, bounded edits to a skill document produce large held-out gains over no-skill and over EvoSkill-style evolution on office and search tasks"]}
claim_correction: The post presents SkillOpt as a new open-source release; the repo was first released 2026-06-02 (v0.1.0) and the paper on 2026-05-22, so this is not new, and "beats hand-crafted prompts and optimizers" holds on the paper's 52 cells with single runs and no intervals.
---

# SkillOpt: Executive Strategy for Self-Evolving Agent Skills (arXiv 2605.23904, microsoft/SkillOpt)

- **URL:** https://arxiv.org/abs/2605.23904 (repo https://github.com/microsoft/SkillOpt)
- **Type:** paper + repo
- **Author / org:** Yifan Yang, Ziyang Gong, Weiquan Huang, Qihao Yang, Ziwei Zhou, Zisu Huang, Yan Li, Xuemei Gao, Qi Dai, Bei Liu, Kai Qiu, Yuqing Yang, Dongdong Chen, Xue Yang, Chong Luo (Microsoft)
- **Date:** paper v1 2026-05-22 (read v2); repo v0.1.0 2026-06-02, v0.2.0 2026-07-02
- **Retrieved:** 2026-09-26, arXiv HTML v2; repo HEAD `79124b37e9a6371e13b753f8bcd7adb1e493ade1` (2026-09-05) via GitHub API, README read via web, not cloned
- **Cited by evidence:** https://x.com/simplifyinAI/status/2103783560029020597 (@simplifyinAI, "MICROSOFT JUST OPEN-SOURCED SELF-EVOLVING AGENT SKILLS")
- **Relevance to a memory stack:** high. A skill document is procedural memory; SkillOpt is a concrete, gated write path for it (propose edit, accept only on a held-out selection split), the same pattern our synthesis borrowed from EvoSkill, with ablations of each part.

## TL;DR
- Treats a natural-language skill file as the trainable "external state of a frozen agent". Rollouts on a train split, an optimizer model reflects on successes and failures in minibatches, proposes add / delete / replace edits, edits are clipped to a "textual learning-rate" budget, and a candidate is accepted "only when strictly improving current selection score; ties are rejected".
- Six-benchmark average on GPT-5.5 direct chat: **+23.5 points** over no skill (Table 1). Best or tied on all 52 (model, benchmark, harness) cells and +5.4 points on average over human-written skills, one-shot LLM skills, Trace2Skill, TextGrad, GEPA and EvoSkill.
- Ablations (Table 3) show the rejected-edit buffer and the slow/meta update matter most (SpreadsheetBench 77.5 -> 55.0 without both).
- Skills transfer: a Codex-trained SpreadsheetBench skill gave +59.7 in Claude Code (22.1 -> 81.8).
- **Claim correction:** not a new release (May/June 2026). All results are single runs on a 2:1:7 train:selection:test split with seed 42; no intervals.
- **Contradiction (partial) with B16:** B16 holds that induced procedures are only a hypothesis and raw trajectories often beat distilled skills. Here induced skills produce large held-out gains and beat EvoSkill; but the paper has no raw-trajectory-in-context arm, so the "raw beats distilled" half is untested, not refuted.

## What it claims / describes
Loop (four phases, paper Section 3):
1. **Rollout evidence:** the frozen target model runs tasks from the train split with the current skill, batch size 40 by default.
2. **Minibatch reflection:** the optimizer model reads successes and failures separately in minibatches of 8 and proposes add / delete / replace edits to the skill document.
3. **Bounded updates:** proposed edits are ranked and clipped to a textual learning-rate budget (default Lt = 4 edits, cosine decay).
4. **Validation gate:** the candidate skill is scored on the selection split and accepted only if it strictly improves the current score. Rejected edits go to a buffer that the optimizer sees later. Every edit is logged in `edit_apply_report.json`.

Final skills are small: 379 to 1,995 tokens (median about 920) from initial skills of 16 to 516 tokens, reached with only 1 to 4 accepted edits.

## Numbers
| metric | value | baseline | setup/benchmark (n) | caveat |
|---|---|---|---|---|
| SearchQA accuracy, GPT-5.5 direct | 87.3 | 77.7 no skill (+9.6) | Table 1, test split 70% of benchmark | single run |
| SpreadsheetBench | 80.7 | 41.8 (+38.9) | Table 1 | single run |
| OfficeQA | 72.1 | 33.1 (+39.0) | Table 1 | single run |
| DocVQA | 91.2 | 78.8 (+12.4) | Table 1 | single run |
| LiveMathematicianBench | 66.9 | 37.6 (+29.3) | Table 1 | single run |
| ALFWorld | 95.5 | 83.6 (+11.9) | Table 1 | single run |
| six-benchmark average gain | +23.5 | no skill | GPT-5.5 direct chat | |
| average margin over other skill methods | +5.4 | human, one-shot, Trace2Skill, TextGrad, GEPA, EvoSkill | 52 cells | "best or tied on all 52" |
| cross-model transfer | +9.4 | no skill | SpreadsheetBench skill GPT-5.4 -> GPT-5.4-mini (Table 4) | |
| cross-harness transfer | 22.1 -> 81.8 (+59.7) | | Codex-trained skill used in Claude Code (Table 4) | |
| cross-benchmark transfer | +3.7 | | OlympiadBench skill on Omni-MATH, GPT-5.4 | |
| ablation: no bounded learning rate | SearchQA 87.1 -> 84.6; SpreadsheetBench 77.5 -> 75.7 | full | Table 3 | |
| ablation: no rejected-edit buffer | SearchQA 87.1 -> 85.5; SpreadsheetBench 77.5 -> 72.9 | full | Table 3 | |
| ablation: no slow/meta update and no buffer | SpreadsheetBench 77.5 -> 55.0 (-22.5) | full | Table 3 | |
| training tokens per test point gained | 0.6M (SpreadsheetBench), 1.1M (OfficeQA), 3.6M (LiveMath), 37.9M (SearchQA) | | Table 6 | cost varies 60x by task |

Note: the ablation table's full-model scores (87.1, 77.5) differ from Table 1 (87.3, 80.7); the paper text as fetched does not explain the difference (possibly a different model or configuration; not stated).

## Mechanism details you could implement
- Split every task set 2:1:7 (train : selection : test) with a fixed seed; gate every write on the selection split only; report on test only.
- Accept strictly greater selection score; reject ties ("prevents silent drift").
- Keep a rejected-edit buffer visible to the proposer so failed ideas stay failed (same idea as the RRSI/EvoSkill experiment ledger in our synthesis section 4).
- Cap edits per round (Lt = 4, cosine decay), i.e. an edit budget, like RRSI's annealed edit budget.
- Reflect on successes and failures separately (contrastive evidence), minibatch 8.
- Log every applied edit with its evidence for audit.

## Limitations, caveats, counter-evidence
- Paper's own limits: needs "reliable automatic verifiers/scoring"; training cost is significant for one-off tasks; one skill may be inadequate for heterogeneous domains; domain heuristics need transfer validation.
- Single runs, no confidence intervals, one split seed. Gains of +5.4 over other optimizers could be within run-to-run noise (inference; noise floor not reported).
- No arm that puts raw successful trajectories in context, so B16's "raw beats distilled" comparison is not addressed.
- No coding-agent benchmark (SWE-style) in the six.
- Selection split is 10% of each benchmark; for small benchmarks that is few items (not stated per benchmark in the fetched text).
- All authors from one organisation; independent replication not found. A later paper (arXiv 2608.09629, "Rethinking Self-Evolving Agents") reports an open-ended optimizer beating SkillOpt in 12 of 14 comparisons (abstract only, not verified here).

## Takeaways for tuning a memory stack
- Procedural memory writes can be gated exactly like our proposed memory writes: propose, score on a held-out selection split, accept only on strict improvement, keep a rejected buffer.
- Expect most value from the gate and the rejected buffer, not from more edits: 1 to 4 accepted edits made the final skills.
- Budget: 0.6M to 38M training tokens per point of test gain; price this before running it per repository.
- Transfer across harnesses can be large (Codex -> Claude Code) but check it per pair.

## Open questions
- Does a skill beat simply retrieving the top-k raw successful trajectories at matched tokens? Not tested.
- Run-to-run variance of the whole loop? Not reported.
- How does the gate behave when the verifier is noisy (our build-time reviews)?

## Grading and labels
- Directness high (held-out test scores). Control medium (strong baselines and ablations; single runs; no raw-trajectory arm). Independence low (single org). Reproducibility medium (MIT repo, commit 79124b37, seed 42). Applicability medium (office/spreadsheet workloads, no coding benchmark).
- Pillar R5 (procedure induction, self-improvement at L2: fixed objective and evaluator, AI chooses edits); secondary R6 (validation protocol).
- Beliefs: **contradicts B16 (partial)**: induced skills shown to improve held-out results substantially; the raw-trajectory comparison is absent. Supports B17 only in that the paper also does not report a wrong-reinforcement rate (bounded survey). Would create: "validation-gated bounded skill edits give large held-out gains over no-skill and EvoSkill on office/search tasks".
- Contradiction row: Contradiction: B16 "Raw trajectories often beat distilled skills; induced procedures are a hypothesis" vs SkillOpt Table 1 (+23.5 average held-out gain from induced skills, +5.4 over EvoSkill). Open: needs a raw-trajectory arm at matched tokens.

## Origin chain
post 2103783560029020597 (@simplifyinAI, no link) -> microsoft/SkillOpt repo (found by name) -> arXiv 2605.23904 v2 -> Table 1 (main), Table 3 (ablations), Table 4 (transfer), Table 6 (cost). Independence: authors are Microsoft; EvoSkill (our local source) is a compared baseline, not a shared author. The post carried no numbers of its own beyond the paper's claims.
