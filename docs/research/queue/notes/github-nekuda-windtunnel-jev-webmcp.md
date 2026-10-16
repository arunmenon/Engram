---
schema_version: 1
artifact_id: N-20261010-02
artifact_type: note
producer: triage
run_id: triage-20261010T014501Z-4cec
created_at: 2026-10-10T01:54:06Z
input_refs: [{"artifact_id": "post:2101196885260460388", "file_id": null, "sha256": null}, {"artifact_id": "post:2100937437325205568", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:nekuda-ai/WindTunnel
claim_cluster: github:nekuda-ai/WindTunnel
feeds: ["decision"]
primary_source: https://github.com/nekuda-ai/WindTunnel
source_commit: 5ca8644e23826ebb30108e7bad240b61043bfe67
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4", "R7"]
memory_stage: routing
priority: 1
tags: {"mechanism": ["decision-model-tool-pick", "small-llm-arguments", "webmcp-tools"], "workload": ["browser-agent"], "lifecycle_stage": ["act"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-configuration results with deterministic state checks", "control": "medium: same 49 tasks and 3 attempts across 21 configurations, but harnesses and turn budgets differ per interface", "independence": "medium: nekuda built the benchmark and the Jev harness; Jev is not theirs", "reproducibility": "high: pinned repo, Apache-2.0 dataset on HF, runner code and redacted transcripts", "applicability": "medium: tool selection by a decision model maps to our routing stage; browser tasks are not memory tasks"}
beliefs_affected: {"supports": ["B12"], "contradicts": [], "would_create": ["With an explicit tool interface, a decision model choosing the tool plus a small LLM writing arguments matches frontier models on success at a fraction of cost"]}
claim_correction: The post says Jev "basically broke the benchmark"; the board shows all nine WebMCP configurations solve 49/49, so Jev's edge is cost and time only; the ratios are about 108x (0.1187/0.0011) and 237x (0.2608/0.0011) on median cost per task, not the posted 112x and 245x, and the board's median cost per task is higher with WebMCP ($0.0011) than DOM ($0.0008), unlike the post's "reducing model cost by 18%".
---

# WindTunnel WebMCP benchmark: Jev (TypeSafe) plus Mercury 2.5 picks tools, 49/49 tasks (nekuda-ai/WindTunnel)

- **URL:** https://github.com/nekuda-ai/WindTunnel ; board https://webmcp.com/benchmark ; dataset huggingface.co/datasets/nekuda/windtunnel
- **Type:** repo plus public leaderboard
- **Author / org:** nekuda (Idan Levin, @0xidanlevin); Jev harness built on browser-use/jev-ultrafast
- **Date:** post 2026-09-19; board v1.2 dated Sep 18, 2026
- **Retrieved:** 2026-10-10; commit 5ca8644e23826ebb30108e7bad240b61043bfe67 (2026-09-18T12:00:05Z, "Publish Jev runners and redacted transcripts (#24)") read via the GitHub API; README and board via WebFetch
- **Cited by evidence:** https://x.com/0xidanlevin/status/2100937437325205568 (@0xidanlevin), https://x.com/egafni/status/2101196885260460388 (@egafni)
- **Relevance to a memory stack:** medium-high. It is the cleanest public test of the split "decision model picks among explicit tools, small generator fills arguments", which is the shape of our routing stage (which store, view or tool handles a request).

## TL;DR
- 49 tasks on 8 self-hosted open-source web apps, 3 attempts each, solved by majority, scored by deterministic application-state checks (no LLM judge).
- Jev + Mercury 2.5 via WebMCP: 49/49, median $0.0011 and 3.2 s per task (rank 1 of 21). Same models via DOM controls ("ultrafast"): 25/49, $0.0008, 5.4 s.
- Every WebMCP configuration on the board solves 49/49 (GPT-5.6 Luna, Gemini 3.6 Flash, Sonnet 5, GPT-6 Astra, Opus 5 ...). The benchmark is saturated under WebMCP; the interface, not Jev, is what moved success.
- Claim correction: see frontmatter. Jev's distinct contribution is cost (about 2x cheaper than the next WebMCP config, Luna at $0.0024) and time.

## What it claims / describes
- Harness: "Jev makes decisions, while Mercury writes arguments or field values and the final answer." At each step Jev sees the task, the available tools and previous results and picks the next tool.
- "The WebMCP and ultrafast DOM setups use separate frozen harnesses, so the comparison is between complete setups, not model alone."
- Tiers: Answer (1-2 steps), Action short (3-5), Action long (6-10), Sensitive action (8-15).
- Score = 60% attempt success, 20% median cost, 20% median time, log-normalised.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| tasks solved, Jev + Mercury 2.5, WebMCP | 49/49 | GPT-6 Astra native WebMCP 49/49 | 49 tasks x 3 attempts | all 9 WebMCP configs 49/49 |
| median cost per task | $0.0011 | Luna native $0.0024; Astra native $0.0171; Astra code exec $0.1187; Astra computer use $0.2608 | same | model cost only, infra excluded |
| median time per task | 3.2 s | Luna native 5.7 s; Astra code exec 16.4 s | same | macOS Docker overhead noted |
| tasks solved, Jev + Mercury, DOM ultrafast | 25/49 | Sonnet 5 DOM + vision 48/49 | same | different harness |
| scorer correction | 19 false negatives fixed | | README | corrected rows marked in CSV |

## Mechanism details you could implement
- Expose actions as explicit named tools; let a decision model choose among them per step; delegate free text (arguments) to a small fast LLM.
- Deterministic outcome checks with seeded values, majority over 3 attempts.

## Limitations, caveats, counter-evidence
- Ceiling effect: success cannot separate WebMCP configurations.
- Turn budgets differ by interface (screen agents get about 3x).
- Benchmark author also built the winning harness.
- Cost per 1,000 attempts is extrapolated from 147 observed attempts.
- Post's "18% lower cost" with WebMCP conflicts with board medians (inference: post may mean total spend across failed attempts; not stated).

## Takeaways for tuning a memory stack
- When the option set is explicit and small, a decision model is a cheap router; when it must navigate an implicit space (DOM), it fails half the time. Our routing stage should present stores and views as explicit options.
- Any routing benchmark we build needs headroom: a saturated success metric turns into a cost race.

## Open questions
- Per-tier results for Jev under DOM; Jev confidence on failed steps.
- Results on harder WebMCP tasks where frontier models fail.

## Grading and labels
- Directness high, control medium, independence medium, reproducibility high, applicability medium (reasons in frontmatter).
- Pillar R9, secondary R4, R7. Stage: routing. Priority 1.
- B12 supports: Jev alone in an open loop (DOM) 25/49; with explicit tools and a helper model, 49/49.
- Would create: decision model plus small arguments-LLM matches frontier success at lower cost when tools are explicit.

## Origin chain
post 2100937437325205568 (@0xidanlevin) quoted by 2101196885260460388 (@egafni) -> webmcp.com/benchmark board v1.2 -> github nekuda-ai/WindTunnel README at 5ca8644 -> this note. Independence: shares browser-use/jev-ultrafast with the monokern article (not noted); polydao (decision trends, 2026-09-30) reports 49/49 on WebMCP, likely the same benchmark, not independent.
