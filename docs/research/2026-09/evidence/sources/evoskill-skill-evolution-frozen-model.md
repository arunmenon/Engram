# EvoSkill: Automated Skill Discovery for Multi-Agent Systems (plus Sentient research roundup)

- **URL:** https://www.sentient.xyz/blog/evoskill-research-self-evolving-agents (roundup); paper https://arxiv.org/abs/2603.02766 ; repo https://github.com/sentient-agi/EvoSkill
- **Type:** vendor blog (roundup) + paper + repo
- **Author / org:** Sentient. Paper authors: Salaheddin Alzubi, Noah Provenzano, Jaydon Bingham, Weiyuan Chen, Tu Vu (Sentient, Virginia Tech)
- **Date:** Roundup 2026-09-24; paper v1 2026-03-03
- **Retrieved:** 2026-09-26 (no local copy; WebFetch of blog, arxiv HTML and GitHub README)
- **Cited by evidence:** Frozen-model self-improvement through harness and skills / 2026-09-24 bafspot
- **Relevance to a memory stack:** high. EvoSkill is procedural memory: a library of skill folders written from failure traces, gated by a held-out validation set, with a frozen model.

Note on sources: the cited blog is a citation roundup ("60+ papers, 100+ institutions") and says little about the mechanism. Mechanism details below come from the arxiv paper (HTML v1) and GitHub README, fetched because the blog links them. Fetches went through a summarizing tool, so prompt text is abridged, not verbatim.

## TL;DR
- Loop: Executor runs tasks, Proposer diagnoses failures (using ground truth) and proposes create or edit of a skill, Skill-Builder writes the skill folder, the new program is scored on a small held-out validation split, and a top-k (k=3) frontier of programs is kept as git branches.
- Skills are folders with a SKILL.md (name, description, trigger conditions, procedure) plus optional scripts and references. Selection at inference is left to the agent reading skill descriptions (inference: same progressive-disclosure pattern as Claude Code skills).
- Gains with Claude Code + Opus 4.5 frozen: OfficeQA 60.6% to 67.9% (paper) or 68.1% (blog and post), SealQA 26.6% to 38.7%, zero-shot transfer of one SealQA skill to BrowseComp 43.5% to 48.8%.
- Libraries stay tiny: single-digit skills per task. Merging unique skills from independent runs beat any single run.
- Counter-evidence from citing papers: raw-trajectory reuse often beats distilled skills (SkillEvolBench); model-generated skills show non-trivial negative transfer (arXiv 2605.23899); EvoSkill needs ground truth for failure diagnosis (CoEvoSkills).

## What it claims / describes
Roles (paper):
1. **Executor agent**: runs tasks under the current "agent program" (base harness plus accumulated skills). Has read access to the repository; its system prompt references available skills.
2. **Proposer agent**: gets executor traces and predicted answers, ground-truth answers ("for root-cause diagnosis, not propagated to skills"), a cumulative feedback history H of all prior proposals, outcomes and score deltas, the list of existing skills, and a failure set F of examples scoring below threshold tau. Method is described as "textual feedback descent".
3. **Skill-Builder agent**: turns the proposal into a concrete skill folder, either a new folder or an edit to an existing SKILL.md.

Loop (README): Base Agent attempts questions with current best program, Proposer analyzes failures, Generator writes skill files or rewrites prompts, Evaluator scores variants on held-out validation set, Frontier tracks top-N programs as git branches. It "extends the feedback-driven approach of GEPA by proposing multiple skill and prompt mutations jointly".

Program storage: each program is a git branch that differs only in skill folders and metadata. Frontier branches are tagged `frontier/*`. Failed candidates' branches are deleted.

Data setup: dataset clustered into K categories with an LLM classifier, then stratified into disjoint train (failure detection), validation (frontier selection), test (final eval, never seen during evolution). Training examples are sampled without replacement, cycling through all before repeating; category-aware sampling.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| OfficeQA exact match (0% tolerance), 5% train | 63.4% | 60.6% | Claude Code, Opus 4.5, 246 questions, ~89,000 pages of Treasury Bulletins | single run |
| OfficeQA, 10% train | 65.8% | 60.6% | same | single run |
| OfficeQA, 15% train | 64.5% | 60.6% | same | more train data did not monotonically help |
| OfficeQA, merge-unique skills from runs | 67.9% (+7.3) | 60.6% | union of unique skills across the runs | blog and bafspot post say 68.1% |
| OfficeQA 10% tolerance | 80.1 / 82.5 / 81.3 / 82.4 (5/10/15/merge) | 79.7% | same | |
| SealQA (seal-0, 111 q) | 38.7% (+12.1) | 26.6% | 10% train split | single run |
| BrowseComp zero-shot transfer | 48.8% (+5.3) | 43.5% | search-persistence-protocol skill from SealQA, 128-example stratified sample | one skill, one task pair |
| Validation set size | 7% of benchmark (17 examples for OfficeQA) | | | very small; noise risk (inference) |
| Frontier size k | 3 | | default | |
| Epochs | 1.5 over training split | | | |
| Scoring tolerances | 0.0, 0.01, 0.025, 0.05, 0.10 weighted; failure threshold 0.8 | | | |
| Skills learned | small single digits per task | | | no total reported |
| Citation stats (blog) | 60+ papers, 100+ institutions, 1,000 GitHub stars, 5 surveys | | | popularity, not evidence of efficacy |
| SkillOpt vs EvoSkill (citing paper) | +14.0% (Codex loop), +3.2% (Claude Code loop) | EvoSkill | arXiv 2605.23904 | competitor claim |
| Trace2Skill vs EvoSkill, SpreadsheetBench-Verified | 65.8%-69.8% vs 33.5%-59.5% | EvoSkill | arXiv 2603.25158 | competitor claim |

## Mechanism details you could implement
- **Skill schema**: folder containing `SKILL.md` with YAML frontmatter, e.g.
  ```yaml
  ---
  name: economic-timeseries-analysis
  description: >
    Streamlined workflow for economic/financial time-series analysis tasks...
  ---
  ```
  followed by procedural instructions, plus optional helper scripts (Python/TypeScript) and references.
- **Write policy (proposer output fields)**: `action` (create | edit), `target_skill`, `proposed_skill` (detailed description), `justification`, `related_iterations`. Rule: create only if no existing skill covers the gap; edit if an existing skill "SHOULD have prevented failure but didn't". Anti-pattern listed: do not propose new skills when existing ones cover similar ground, consolidate instead. Proposer must use a Brainstorming skill, brainstorm 2-3 approaches, apply YAGNI.
- **Skill-builder directive**: "Before implementing any skill, always read and follow the '.claude/skills/skill-creator/SKILL.md' skill."
- **Ground-truth firewall**: ground truth is visible to the proposer for diagnosis but not copied into skills.
- **Feedback history H**: log of every proposal, outcome and score delta, fed back to the proposer so it does not repeat failed ideas.
- **Acceptance rule**: candidate enters frontier if its validation score beats the weakest frontier member, or frontier has fewer than k members. If size > k, evict argmin score. Parent for next iteration chosen round-robin over frontier.
- **Pruning**: there is no per-skill pruning or retirement mechanism described. Pruning is at the program level (losing branches deleted, weakest frontier member evicted). A skill disappears only if the program carrying it falls off the frontier or the proposer edits it.
- **Merge**: "skill-merge" configuration aggregates unique skills from independent runs; it was the best OfficeQA result.
- **Config defaults (README)**: `iterations = 20`, `frontier_size = 3`, `concurrency = 4`, `no_improvement_limit = 5` (early stop), `train_ratio = 0.18`, `val_ratio = 0.12`, modes `skill_only` or `prompt_only`. Scorers: `multi_tolerance` (default), `exact`, `llm` (judge), `script`, `harbor` (containerized). CLI: `evoskill init | run [--docker --remote --continue] | eval | skills | diff`. Note README defaults (18/12%) differ from paper splits (5-15% train, 7% val).
- **Harnesses**: Claude Code, OpenCode (v1.4.0+), OpenHands, Goose (v1.25.0+), Codex CLI, Harbor.
- **Example learned skills**: `data-extraction-verification` (Treasury table cell misreads, metric confusion), `quantitative-analysis-methodology` (mandatory validation checkpoints), `search-persistence-protocol` (term-interpretation expansion, three-source minimum verification, an explicit "unable to find" protocol, enumeration completeness checks).

## Limitations, caveats, counter-evidence
- Paper: single run per configuration due to cost, no seed variance; two benchmarks; transfer shown for one task pair. README lists "evolution without a benchmark" and "continuous evolution" as open.
- Needs labeled ground truth to diagnose failures (CoEvoSkills critique). A memory stack in deployment usually lacks this (inference).
- Validation split of 17 examples means a one-question swing is about 6 points (inference). No noise floor is applied, unlike RRSI.
- SkillEvolBench (180 tasks, 6 environments): "Current agents adapt locally but rarely form robust reusable skills, and raw-trajectory reuse frequently outperforms distilled skills."
- arXiv 2605.23899: "Model-generated skills help on average but show non-trivial negative transfer; extractor and consumer turn out to be decoupled capabilities."
- Experience Compression Spectrum (AWS, arXiv 2604.15877) places EvoSkill as a "Level-2 procedural-skill system": episodic memory 5-20x compression, procedural skills 50-500x, declarative rules 1000x+.
- Production deployments claimed (Bloomberg, Alibaba Taobao, ByteDance, Elastic, Shanghai AI Lab) without details.

## Takeaways for tuning a memory stack
- Treat skill writes as proposals that must beat the current best configuration on a held-out split before they persist; keep top-k memory configurations rather than a single mutable store.
- Force a create-vs-edit decision with a "does an existing entry cover this?" check before any write. This is the main anti-bloat control.
- Keep a proposal ledger (what was tried, score delta) separate from the memory itself, and feed it to the writer.
- Version memory states as git branches so a regression can be diffed and rolled back.
- Merge unique entries across independent runs, then re-validate: union beat each individual run here.
- Add what EvoSkill lacks: per-entry retirement, a noise floor, and a comparison against plain raw-trajectory retrieval.

## Open questions
- Does library growth past single digits hurt? Not tested.
- How does selection behave with 50+ skills whose descriptions compete for the context window?
- Seed variance of the gains.
- Can a verifier or self-play (CoEvoSkills, Ctx2Skill) replace ground truth without drift?

---
