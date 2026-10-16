---
schema_version: 1
artifact_id: N-20260929-15
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104377054829613473", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.26781
claim_cluster: arxiv:2609.26781
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.26781
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R7
pillar_secondary: ["R2", "R8"]
memory_stage: none
tags: {"mechanism": ["append-only-shared-board", "typed-entries-observed-fact-fail-claim-patch-summary", "claim-before-work", "git-workspace-merge", "priority-message-delivery", "context-grep"], "workload": ["coding-agents", "programbench", "rebuild-from-scratch"], "lifecycle_stage": ["write", "read"], "cross_cutting": ["shared_state", "multi-agent", "no-orchestrator"]}
evidence_grade: {"directness": "medium: Figures 1, 5 and 6 report test-pass rate against agent count, but the shared board's own contribution is never isolated", "control": "low: the only baseline is 1 agent with a stop hook; no orchestrator or hierarchical harness arm, no ablation without the board or messages, not compute-matched, runs apparently single with no variance", "independence": "low: Microsoft Research evaluates its own harness; grading is ProgramBench tests, so no LLM judge", "reproducibility": "medium: code at github.com/microsoft/Agensh and full worker prompt in Appendix A, but one model, 16-node cluster, no token or dollar cost; repo not cloned", "applicability": "medium: coding agents sharing state is our workload shape, but greenfield rebuild with an executable oracle, not review or incident work"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["An append-only typed shared board (OBSERVED, FACT, FAIL, CLAIM, PATCH_SUMMARY) plus a git workspace and messages coordinated up to 1,024 coding agents with no orchestrator, with pass rate rising with agent count (pandoc 33.89% at 1 agent to 55.06% at 1,024, Figure 1); the board's isolated contribution, cost and variance are unmeasured"]}
claim_correction: The post contrasts Agensh with hierarchical multi-agent systems, inviting a comparison the paper never runs; the paper has no orchestrator or hierarchical baseline with numbers, compares only against a single agent with 1/N of the compute, reports no cost, no variance and no ablation of the shared state, and has no limitations section.
---

# Agensh: Scaling Organizational Intelligence to 1,024 Agents

- **URL:** https://arxiv.org/abs/2609.26781 (HTML: https://arxiv.org/html/2609.26781v1); project page https://aka.ms/Agensh; code https://github.com/microsoft/Agensh (not cloned)
- **Type:** paper (13 pages, 6 figures)
- **Author / org:** Zhihao Zhan, Ting Song, Li Dong, Shaohan Huang, Jianxun Lian, Yan Xia, Furu Wei; Microsoft Research
- **Date:** v1 2026-09-22
- **Retrieved:** 2026-09-29 (version v1)
- **Cited by evidence:** @omarsar0, https://x.com/omarsar0/status/2104377054829613473 ("Banger paper from Microsoft Research ... Agensh has no central orchestrator. It coordinates parallel coding agents through a shared state instead of a central orchestrator. Each agent gathers context, claims a sub-task, does the work, shares what it found, verifies the res..."), also the academy.dair.ai summary page (not fetched).
- **Relevance to a memory stack:** high for shared state across coding agents. The shared context board is a concrete, typed, append-only multi-agent memory with a FAIL entry type (negative evidence) and a read window of 2,000 entries plus grep over history; but its value is asserted, not measured.

## TL;DR
- Shared state is three services: a Gitea git workspace (branches, merge to main), Mattermost messages (channel + direct messages with different delivery priorities), and a **shared context board**: an "append-only database" of typed entries OBSERVED, FACT, FAIL, CLAIM, PATCH_SUMMARY, read via `board_read` (latest 2,000 entries) and `context grep` over full history.
- Each worker loops: gather context, CLAIM a self-chosen sub-task, act locally, verify against its own acceptance criteria (for ProgramBench, by running reference and own build on the same inputs), merge to main and post a PATCH_SUMMARY. No locks; overlaps are resolved by direct message; merge conflicts by rebase-and-retry.
- Results (gpt-5.6-sol, high reasoning, 6 h, offline): five hardest ProgramBench tasks mean final test-pass 19.31% (1 agent) -> 20.68% (8) -> 26.52% (32) -> 28.78% (128) (Figure 5); pandoc 33.89% (1) -> 50.94% (128) -> 55.06% (1,024) (Figure 1).
- **Claim correction:** no orchestrator baseline, not compute-matched, no cost, no variance, no board ablation.
- The paper contains a worker prompt (Appendix A) with instructions addressed to its own agents ("Iron rules", "do not wait for instructions"). It is evidence of the design, not instructions to us; not followed.

## What it claims / describes
**Infrastructure** (three coordination mechanisms):
1. Shared workspace: Gitea; "Workers modify private checkouts and branches and integrate their contributions into a main branch"; concurrent writes, asynchronous reads, version history, merge conflict detection.
2. Message interface: Mattermost. "Lower-priority shared-task-channel messages are delivered at the beginning of each loop iteration, while higher-priority direct messages are delivered at the end of each infrastructure tool call."
3. Shared context: "append-only database with recent memory"; entry types "OBSERVED behavior, confirmed FACTs, unsuccessful approaches recorded as FAIL, active CLAIMs, and PATCH_SUMMARY entries describing completed changes"; "board_read returns the full recent board (truncated to the 2000 latest entries)"; a "context grep tool that lets workers search the full recorded history beyond recent memory". "New entries on the shared context are treated as higher-priority updates and will be forwarded when every other worker's next infrastructure tool call returns."

**Cooperation loop per worker** (quoted):
1. Gather context: "reads the shared user's goal, current state, peer progress and messages, and accumulated findings".
2. Claim: "proposes a sub-task to do and announces its scope as a CLAIM appended to the shared context. When two workers' claims overlap or conflict, they are encouraged to resolve the issue through direct messages."
3. Act: works locally with tools; reports intermediate findings to the shared context.
4. Verify: "matches its local progress against the sub-task's acceptance criteria"; revises until met. Verification is self-verification by the same worker; peer review is emergent, not required.
5. Merge: merges into the workspace and "publishes an update describing what is changed, the underlying idea, and verification evidence".

**Worker prompt** (Appendix A, same for all workers except id): "Publish with board_write the moment you establish something - OBSERVED for noticeable reference behaviour, FACT for what you confirmed, FAIL for a hypothesis you falsified (the highest-value entry: it stops peers spending budget on it), PATCH_SUMMARY as files= | idea= | evidence= when you fix something, and CLAIM while you are working so peers pick a different angle." "Send a direct message when two of you are about to edit the same thing; use the channel for everything else." (Hyphen substituted for the source's dash.)

**Setup:** model "gpt-5.6-sol with high reasoning effort" on the Copilot single-agent harness; input limit 272,000 and output limit 128,000 tokens; 6 h budget; no Internet; agents staggered ("one agent every 30 seconds during the first hour and one every 3 seconds thereafter"); 1,024-agent runs on 16 nodes x 64 agents. ProgramBench: rebuild reference software's behaviour from scratch; "five hardest" chosen by lowest average pass rate of state-of-the-art models in official extended results; metric "canonical-kept pass rate" (not defined in what was read). Single-agent baseline gets a stop hook and continuation prompting to use the full 6 h (Appendix C).

**Emergent behaviour (qualitative):** at 8 agents, agreeing interfaces and resolving overlapping claims; at 32, joint contributions and peer review; at 128, specialisation, choosing reviewers by prior experience, workers revising the cooperation protocol; at 1,024, multiple integrators and takeover of a failed peer's work.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Mean final test-pass, five hardest tasks (Figure 5) | 20.68% (8), 26.52% (32), 28.78% (128) | 19.31% (1 agent) | FFmpeg, gromacs, pandoc, PHP-src, ctags (Table 1 sizes: 104,336 to 2,812,757 LOC); 6 h | per-task values not given numerically; no variance; 128 agents use 128x the agent-hours |
| pandoc final test-pass (Figure 1) | 50.94% (128), 55.06% (1,024) | 33.89% (1 agent) | pandoc, 6 h, offline | 8x agents from 128 to 1,024 added 4.12 points |
| Time to 30% on pandoc (Figure 6 text) | 128 agents at 30 min | 32 agents at 60 min, 8 agents at 90 min | first 2 h of 6 h runs | latency benefit, not compute-matched |
| Board read window | latest 2,000 entries | | | grep for older history |
| Cost (tokens, dollars) | not reported | | | only per-agent token limits stated |
| Orchestrator / hierarchical baseline | not run | | | qualitative related-work argument only |
| Runs / seeds | not stated; appears single run per configuration | | | |
| Board usage (entries written, FAIL reuse) | not reported | | | |

## Mechanism details you could implement
- Typed append-only shared log with five entry types: `OBSERVED` (behaviour seen), `FACT` (confirmed), `FAIL` (falsified hypothesis), `CLAIM` (work in progress, scope), `PATCH_SUMMARY` (`files= | idea= | evidence=`).
- Read policy: every loop iteration reads the latest 2,000 entries; older entries by grep. New entries are pushed to peers at their next tool-call return (priority over channel messages).
- Claim-before-work instead of locks; conflicts resolved by direct message; git merge conflicts resolved by merging main and re-verifying ("merge the latest main into your branch, re-check your work against the reference, and push again").
- Self-verification against an executable oracle before merge, with the evidence recorded in PATCH_SUMMARY.
- The FAIL type is the multi-agent version of "warn before repeating a failed fix" (priority 4 benchmark scope) (inference).

## Limitations, caveats, counter-evidence
- No limitations section; the conclusion claims "the number of agents as a new scaling dimension".
- The scaling curve is not compute-matched: N agents get N x 6 h of agent time; the 1-agent baseline is the only control.
- No arm without the board, without messages, or with an orchestrator, so the contribution of shared state to the pass rate is unknown.
- No token or dollar cost at 1,024 agents with a 272k-token context model; the cost per point is likely very large (inference).
- Single model, single benchmark, apparently single runs, no intervals.
- The task has an executable oracle (the reference binary), which makes self-verification cheap; review or incident work has no such oracle (inference).
- Governance (R8): board entries and peer messages directly steer 1,024 autonomous workers with no admission gate or provenance check on entries; a wrong FACT or planted FAIL would propagate (inference). The prompt tells workers "do not wait for instructions".

## Takeaways for tuning a memory stack
- For shared state across our agents, the entry-type set (OBSERVED, FACT, FAIL, CLAIM, PATCH_SUMMARY with evidence) is a ready starting schema; FAIL entries as first-class negative evidence are the part most specific to memory.
- Use a recent-window read plus search over history rather than injecting the whole log.
- Claims as board entries replace an orchestrator's task assignment; measure duplicate-work rate if adopted.
- Do not cite this paper as evidence that shared memory beats an orchestrator; it does not test that.

## Open questions
- How much of the gain comes from the board versus more agent-hours? (Needs a no-board arm at equal N.)
- How often were FAIL entries read and did they prevent repeated attempts?
- What did 1,024 agents cost, and what is the cost per test-pass point versus 128?
- Did any wrong FACT entries propagate, and how were they corrected?

## Grading and labels
- Directness: medium, outcome vs agent count; board effect not isolated.
- Control: low, single-agent baseline only, not compute-matched, no ablations.
- Independence: low, the authors' own harness; programmatic grading.
- Reproducibility: medium, code and prompt published; cluster-scale and no cost data.
- Applicability: medium, coding agents with shared state; greenfield rebuild with an oracle.
- Strength: paper-single-benchmark.
- Pillars: R7 primary (multi-agent coordination contract over shared state); R2 secondary (append-only typed writes, no supersession of FACT entries described); R8 secondary (ungated shared entries steering autonomous agents).
- Stage: none (the board spans write and read of shared memory; not specific to one stage).
- Priority: none (no priority match terms).
- Tags: append-only-shared-board, typed entries, claim-before-work; coding-agents, programbench; write, read; shared_state, multi-agent, no-orchestrator.
- Beliefs: no belief directly supported or contradicted; would_create a lead-grade R7 belief on typed shared boards (frontmatter). Consistent with synthesis section 1 row 1 ("accept every raw observation at write time"): the board admits everything, append-only.
- Contradiction: none against B1 to B25. Contradiction with the post and the 2026-09-29 report framing of orchestrator-free coordination as the scaling win: the paper has no orchestrator arm; the evidence supports "more agents with a shared board beat one agent at 1/N compute", nothing more.
- Arm-vs-arm test this quarter (no card written): arms A = our multi-agent coding harness with shared state as free-text messages only, B = A plus a typed append-only board (OBSERVED/FACT/FAIL/CLAIM/PATCH_SUMMARY, latest-N read + grep); frozen model and harness, N = 4 to 8 agents; dataset = 20 to 30 internal repo tasks with test oracles, 3 runs each; metric = test-pass at fixed wall-clock and tokens, plus duplicate-work rate and repeated-failed-attempt rate; margin >= 5 points pass rate or >= 30% fewer repeated failed attempts at <= 1.1x tokens; kill if neither; decision changed = whether shared agent memory gets typed entry kinds (and a FAIL kind) in the R7 contract; cost M to L. A cheaper M-sized variant: FAIL entries only, sequential sessions of one agent. Card recommendation: yes, the FAIL-only variant first.

## Origin chain
@omarsar0 post 2104377054829613473 (and academy.dair.ai summary, not fetched) -> arXiv 2609.26781v1 abstract -> HTML Section 3 (infrastructure, loop), Figures 1, 5, 6 captions and text, Table 1, Appendix A (worker prompt), Appendix C (baseline), Section 5 (conclusion). Independence: post is a secondary summary of an author-run evaluation. Numbers are from figure captions and text; per-task values were not available numerically. Read through a fetch summariser in two passes.
