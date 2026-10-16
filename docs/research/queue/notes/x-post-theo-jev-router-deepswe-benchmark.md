---
schema_version: 1
artifact_id: N-20261004-01
artifact_type: note
producer: triage
run_id: triage-20261004T014502Z-25fb
created_at: 2026-10-04T01:52:17Z
input_refs: [{"artifact_id": "post:2103774771788108008", "file_id": null, "sha256": null}, {"artifact_id": "post:2103895901140042044", "file_id": null, "sha256": null}, {"artifact_id": "post:2103924415570514310", "file_id": null, "sha256": null}, {"artifact_id": "post:2103865678570954891", "file_id": null, "sha256": null}, {"artifact_id": "post:2103869739193815333", "file_id": null, "sha256": null}, {"artifact_id": "post:2103915638133792999", "file_id": null, "sha256": null}, {"artifact_id": "post:2103907158098337838", "file_id": null, "sha256": null}, {"artifact_id": "post:2103923207573271015", "file_id": null, "sha256": null}, {"artifact_id": "post:2103823294076174681", "file_id": null, "sha256": null}, {"artifact_id": "post:2103869226792427708", "file_id": null, "sha256": null}, {"artifact_id": "post:2103827407304073720", "file_id": null, "sha256": null}, {"artifact_id": "post:2103930174089937179", "file_id": null, "sha256": null}, {"artifact_id": "post:2103908181886050572", "file_id": null, "sha256": null}, {"artifact_id": "post:2103927687534477801", "file_id": null, "sha256": null}, {"artifact_id": "post:2103820225045205141", "file_id": null, "sha256": null}, {"artifact_id": "post:2103824574802452627", "file_id": null, "sha256": null}, {"artifact_id": "post:2103913499932197132", "file_id": null, "sha256": null}, {"artifact_id": "post:2103826446548357584", "file_id": null, "sha256": null}, {"artifact_id": "post:2103819181724475399", "file_id": null, "sha256": null}, {"artifact_id": "post:2103928734403150166", "file_id": null, "sha256": null}, {"artifact_id": "post:2103930381439209581", "file_id": null, "sha256": null}, {"artifact_id": "post:2103872411577765911", "file_id": null, "sha256": null}, {"artifact_id": "post:2103824605831995602", "file_id": null, "sha256": null}, {"artifact_id": "post:2103862454073659547", "file_id": null, "sha256": null}, {"artifact_id": "post:2103818894188105849", "file_id": null, "sha256": null}, {"artifact_id": "post:2103818560162148378", "file_id": null, "sha256": null}, {"artifact_id": "post:2103866697346318654", "file_id": null, "sha256": null}, {"artifact_id": "post:2103802957926207861", "file_id": null, "sha256": null}, {"artifact_id": "post:2103882056686281061", "file_id": null, "sha256": null}, {"artifact_id": "post:2103869984812286268", "file_id": null, "sha256": null}, {"artifact_id": "post:2103872864696807810", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x:2103774771788108008
claim_cluster: x:2103774771788108008
feeds: ["decision", "memory"]
primary_source: https://x.com/theo/status/2103774771788108008
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R4", "R6"]
memory_stage: routing
priority: 1
tags: {"mechanism": ["model-router", "per-request-effort-selection", "system-one-decision-model"], "workload": ["agentic-coding", "DeepSWE"], "lifecycle_stage": ["routing"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: the builder ran the benchmark and published a results chart, but no logs or per-task table", "control": "medium: same harness, same 20 tasks for all three arms, but 1 attempt per task and no seeds", "independence": "high: independent developer, not TypeSafe or OpenRouter", "reproducibility": "low: task ids, router config and logs not published", "applicability": "medium: coding-agent workload close to ours, but routing is per request on a gateway, not per memory-stage decision"}
beliefs_affected: {"supports": ["B13"], "contradicts": [], "would_create": ["Per-request model routing by Jev Router on an agentic coding benchmark matched a fixed low-effort frontier model on score and cost but took about 4x longer per task (one builder, n=20)"]}
claim_correction: Posts relay "roughly the same performance, slightly more cost, almost 5x longer"; the chart shows 16/20 for both, $1.50 vs $1.46 per task and 19.9 vs 4.6 min per task (4.3x, not 5x), and a third arm (GPT-6 Astra xhigh, 17/20, $4.42, 12.8 min) the posts mostly omit
---

# Jev Router (OpenRouter typesafe/jev-router) vs GPT-6 Astra low and xhigh on 20 DeepSWE tasks (Theo, t3.gg)

- **URL:** https://x.com/theo/status/2103774771788108008 (chart: https://pbs.twimg.com/media/HTIbo_uaUAAv-zN.jpg)
- **Type:** X post (builder benchmark, results in an attached chart)
- **Author / org:** Theo (@theo), CEO of t3.gg / T3 Chat; independent of TypeSafe and OpenRouter
- **Date:** 2026-09-26
- **Retrieved:** 2026-10-04 via the fxtwitter mirror API (post text and media URL), chart downloaded to repos/img/theo-jev-router.jpg and read; version n/a
- **Cited by evidence:** @theo 2103774771788108008 (quoted or discussed by 30 staged posts, among them @kunchenguid 2103895901140042044, @stretchcloud 2103865678570954891); quotes the OpenRouter launch post 2103610898690855161
- **Relevance to a memory stack:** medium, it is the first independent cost and latency measurement of a System One model used as a request-level router on a coding workload

## TL;DR
- On 20 DeepSWE tasks, same harness as the public leaderboard, 1 attempt per task: Jev Router 16/20 (80%), GPT-6 Astra low 16/20 (80%), GPT-6 Astra xhigh 17/20 (85%) (chart).
- Cost per task: Jev Router $1.50, Astra low $1.46, Astra xhigh $4.42 (chart, "Cost is what OpenRouter billed per task").
- Time per task: Jev Router 19.9 min, Astra low 4.6 min, Astra xhigh 12.8 min. The router was slower than even the xhigh arm (chart).
- Claim correction: the "almost 5x longer" in the post is 4.3x on the chart; the xhigh arm, which most reposts drop, shows the router did not buy the extra task either.
- n=20, one attempt: a one-task difference is noise (inference); the solid finding is latency, not score.

## What it claims / describes
OpenRouter launched `typesafe/jev-router` on 2026-09-25: "a cache-aware model router powered by Jev and @typesafeai ... picks the best model and reasoning effort for each request, balancing quality, speed, and cost" (quoted launch post 2103610898690855161). Theo ran the router as the model behind a coding agent on DeepSWE and compared it with calling GPT-6 Astra directly at low and at xhigh reasoning effort. Post text, verbatim: "I stayed up til 2am and spent $1,000 benchmarking Jev Router so you don't have to. Performance on DeepSWE was roughly the same as GPT-6 Astra on low. It costs slightly more, and it took almost 5x longer to run."

Chart subtitle, verbatim: "DeepSWE, 20 tasks, same harness as the public leaderboard, 1 attempt per task." Footer: "Cost is what OpenRouter billed per task. Time is the agent's mean working minutes per task. All scales start at 0."

Not stated: which models the router actually chose per request, how effort was distributed, which 20 tasks, whether the router's own decision latency or the downstream model choice drives the extra time, whether cache hits differed.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Score | Jev Router "80% 16/20" | GPT-6 Astra low "80% 16/20"; xhigh "85% 17/20" | DeepSWE, 20 tasks, 1 attempt (chart) | n=20, no seeds; one task = 5 points |
| Cost per task | "$1.50" | low "$1.46"; xhigh "$4.42" | OpenRouter-billed (chart footer) | total spend "$1,000" (post) includes runs not shown (inference) |
| Time per task | "19.9 min" | low "4.6 min"; xhigh "12.8 min" | mean working minutes per task (chart footer) | 19.9/4.6 = 4.3x (computed); post says "almost 5x" |

## Mechanism details you could implement
- The router decides model and reasoning effort per request (launch post). Effort is chosen per request, not per task, so a long agent loop pays the routing decision on every turn (inference).
- @kunchenguid's critique (2103895901140042044, opinion): "a prompt without surrounding context is simply not enough signal to judge complexity"; the same prompt is easy in a toy repo and hard in the Linux kernel. If you route, route on task state (repo size, recent failures), not on the request text (inference from the critique).
- Measure a router against fixed-effort baselines at both ends (low and max), on cost, score and wall-clock time; Theo's chart is a usable template.

## Limitations, caveats, counter-evidence
- 20 tasks, 1 attempt each, no confidence intervals; the score ties are not evidence of equal quality.
- No logs, no task list, no router decisions published; the latency cause is unknown.
- Launch-week router; settings may have changed since 2026-09-26.
- Counter-evidence elsewhere: mika_systems (2103921273852108955) relays a Jev effort-selection result with 98.5% fewer thinking tokens on six tasks; that source is unidentified and was not noted (see triage log). Earlier bus note blog-neonronin-jev-router-latency.md measured router latency on the gateway path.

## Takeaways for tuning a memory stack
- Do not assume a System One router saves money on agent loops: here it matched a fixed low-effort model on cost and lost 4x on time.
- Any routing stage we test needs a fixed-low and a fixed-high arm and must report wall-clock time, not only tokens.
- Prefer routing on state that a memory stack already holds (task history, repo facts) over routing on the bare request (inference).

## Open questions
- Is the extra time the router's own call, more agent turns, or slower downstream models?
- Does the result hold over more tasks or with several attempts per task?
- Would routing per task (once) instead of per request remove the latency cost?

## Grading and labels
- Directness: medium, first-hand chart, no raw data.
- Control: medium, matched harness and tasks, three arms, single attempt.
- Independence: high, builder unaffiliated with TypeSafe or OpenRouter.
- Reproducibility: low, nothing released beyond the chart.
- Applicability: medium, coding agent, but request-level gateway routing.
- Pillars: R9 primary (Jev as a router), R4 (when to automate the effort decision), R6 (benchmark integrity, n=20). Stage: routing. Priority 1.
- Beliefs: supports B13 (escalation to a bigger option is not automatically better: xhigh cost 3x for one task); would create a belief on router cost and latency on coding agents.
- Contradiction rows: none.

## Origin chain
OpenRouter launch post 2103610898690855161 (2026-09-25), then Theo's benchmark post 2103774771788108008 with chart image HTIbo_uaUAAv-zN.jpg, then the chart rows "Score (of 20 tasks)", "Cost per task", "Time per task", then this note. The 30 staged posts are reposts, quotes and commentary of the same chart; no independent replication in the cluster. Independence: one builder, one harness; DeepSWE harness shared with the public leaderboard.
