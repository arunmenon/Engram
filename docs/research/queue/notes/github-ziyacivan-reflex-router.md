---
schema_version: 1
artifact_id: N-20260926-11
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2102668315290198315", "file_id": null, "sha256": null}, {"artifact_id": "post:2103734688053448993", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:ziyacivan/reflex-router
claim_cluster: github:ziyacivan/reflex-router
feeds: ["decision"]
primary_source: https://github.com/ziyacivan/reflex-router
source_commit: 54271137a61f261df2d7d38f13adabf129849ac2
strength: repo-pinned
pillar_primary: R4
pillar_secondary: ["R6", "R7"]
tags: {"mechanism": ["per-task model routing", "decision-model tier choice", "shadow mode", "prompt-cache switch guard", "randomised A/B arms"], "workload": ["Claude Code engineering sessions"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: decision logs and list-price cost by routed pair from real sessions", "control": "low: no quality measurement (randomised arms routed 11 / control 22), cost estimates only", "independence": "medium: single maintainer, no vendor tie stated", "reproducibility": "medium: code pinned; logs are the maintainer's own and not public", "applicability": "high: exactly our workload (coding-agent sessions in Claude Code)"}
beliefs_affected: {"supports": ["B13"], "contradicts": [], "would_create": ["In real Claude Code work, per-task model routing saves little: tool-loop continuations hold 55 to 73% of tokens and cannot be routed without cache penalties, and upward moves cancel downward savings"]}
claim_correction: The 15-hour post attributes the loss to upgrades and a stale pin; the repo confirms this, and adds that a later three-day log netted about $0.03 and a five-day work log saved an estimated 3.4% of spend, all as list-price estimates with no quality measurement.
---

# reflex-router: a Jev-driven model router for Claude Code (ziyacivan/reflex-router)

- **URL:** https://github.com/ziyacivan/reflex-router
- **Type:** repo
- **Author / org:** ziyacivan (single maintainer)
- **Date:** HEAD `54271137a61f261df2d7d38f13adabf129849ac2` (2026-09-25 18:22 +0300, "chore(release): 0.5.8")
- **Retrieved:** 2026-09-26, shallow clone at repos/reflex-router (read only). Read: README.md, CHANGELOG.md (0.3.7 and Laya sections), docs/observations.md (2026-09-22 15-hour log, 2026-09-23 Laya vs Jev, 2026-09-24 three-day and five-day logs)
- **Cited by evidence:** https://x.com/ziyacivan/status/2102668315290198315 (@ziyacivan: "I ran my model router on 15h of real Claude Code work. It cost $0.95 more than it saved"), https://x.com/ziyacivan/status/2103734688053448993 (@ziyacivan, replying to OpenRouter's jev-router launch)
- **Relevance to a memory stack:** medium-high. The only builder log we have of decision-model routing on real coding-agent work, with the cost structure of Claude Code sessions (where tokens go, what a model switch costs in cache writes). Directly relevant to where a decision layer can save anything in an engineering agent.

## TL;DR
- Loopback proxy between Claude Code and the Anthropic API. For each "positively identified start of work" (typed prompt, subagent's first request) one Jev call asks the least capable tier that will do the task (Haiku, Sonnet, Opus) and how much reasoning it needs. Tool-loop steps and side calls are never sent to Jev.
- **15 hours, route mode (2026-09-22):** 295 classified requests, 8 sessions; section 8 **-$0.95** on 55 routed requests ($3.38 at requested model vs $4.33 at model sent). Loss came from upgrades (Haiku -> Opus 5 -$0.67, Sonnet -> Opus 5 -$1.20; 15 of these were one subagent on a stale pin); the downgrade pair Opus 5.5 -> Sonnet 5 saved +$0.91.
- **Three days (2026-09-22 to 24):** 27 sessions, 2,209 requests, ~384M tokens: 96 moved down (-$3.76), 38 moved up (+$3.73), **net $0.03**. Main-chat tool-loop continuations were 73.4% of tokens, so routing could touch at most 26.3%.
- **Five days, second machine:** 2,517 requests, ~631M tokens: estimated $7.11 saved, **3.4% of spend** ($206.79 -> $199.68).
- Quality of routed turns is **not measured** (randomised arms: routed 11 / control 22). All dollar figures are "list-price estimates over recorded token counts, not bills".

## What it claims / describes
- **Decide:** one backend call per new unit of work, two questions (tier; reasoning effort). Rule `mass` with `REFLEX_MASS_EPS` 0.10; moves below Opus only when P(opus) <= 0.10.
- **Guard:** refuses main-chat switches whose prompt-cache rewrite would cost more than the saving (`over_limit`); e.g. moving a conversation down "wrote its whole context once on the target (63,689 tokens on Sonnet in one case)".
- **Shadow mode first:** logs what it would route (`~/.reflex/decisions.jsonl`), `reflex report` has 15 sections incl. outcome rates with an explicit "insufficient data" line below 20 windows.
- **Upgrades** opt-in (`REFLEX_UPGRADES`), off by default after the 15-hour loss.
- **Privacy:** only redacted task descriptions go to the decision backend; no telemetry.
- **Local alternative (Laya):** zero-shot Laya picked Opus for essentially every prompt (0/0/30 on the 30-prompt author set vs Jev 13/5/12 and 27/30 exact); a distilled calibration head got 17/30; Laya work stopped 2026-09-24.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| 15-hour net | -$0.95 | requested model | 55 routed of 295 requests, 8 sessions | list-price estimate |
| Haiku 4.5 -> Opus 5 | -$0.67 | $0.17 -> $0.84 | 5 records | upgrade |
| Sonnet 5 -> Opus 5 | -$1.20 | $0.80 -> $1.99 | 15 records | one subagent, stale pin |
| Opus 5.5 -> Sonnet 5 | +$0.91 | $2.41 -> $1.50 | 35 records | |
| three-day net | +$0.03 | | 2,209 requests, 27 sessions, ~384M tokens | 96 down, 38 up |
| token share: main-chat continuations / subagents / side calls / new turns | 73.4% / 12.9% / 8.5% / 5.2% | | three-day log | routable at most 26.3% |
| guard refusals | 18 of 26 main-chat switches | | three-day log | median penalty $1.09 |
| Jev latency | p50 414 ms (381 ms reused connection) | | n = 165 | |
| five-day saving | $7.11, 3.4% of spend | $206.79 | 2,517 requests, ~631M tokens | no A/B |
| Jev on author set | 27/30 exact | Laya 12/30 | 30 prompts, author labels | not ground truth |
| randomised arms | routed 11 / control 22 | | combined logs | too small for quality |

## Mechanism details you could implement
- Decide only at the start of a unit of work; never on tool-loop continuations (they carry the cache and most of the tokens).
- Guard every model switch with its prompt-cache rewrite cost; refuse when the penalty exceeds the expected saving.
- A pin belongs to the requested model it was decided under; drop it when the requested tier changes (0.3.7 fix).
- Clamp `max_tokens` to the target tier's maximum on retarget (Opus 5.5 128000 vs Haiku 4.5 64000).
- Run shadow first and require >= 20 outcome windows per arm before reading quality.

## Limitations, caveats, counter-evidence
- README: "Single-user alpha", "Untuned thresholds", "Only one organic correction across 44 scored windows", macOS only, Claude Code 2.1.277 to 2.1.282.
- No quality metric; savings are estimates at list price; one maintainer's work.
- The five-day log's 3.4% saving came from subagent-heavy work; personal log netted zero.

## Takeaways for tuning a memory stack
- A decision layer inside a coding agent can only touch the small share of tokens at unit-of-work boundaries (5 to 26% here); the rest is tool-loop context. Put decision calls where the tokens are decided (what enters context: memory admission and curation), not only on model choice (inference).
- Cache economics dominate: any per-turn change to the context prefix (including injecting memories) should be priced as a cache rewrite.

## Open questions
- Quality of routed vs unrouted turns with adequate randomised arms? Not measured.
- Would routing only subagents (`REFLEX_MAIN_CHAT=never`) be positive consistently? Partial evidence from the five-day log.

## Grading and labels
- Directness high; control low; independence medium; reproducibility medium (commit 54271137); applicability high.
- Pillar R4 (routing/escalation as a decision with error costs). Secondary R6 (cost accounting, shadow vs route) and R7 (proxy between harness and API).
- Beliefs: supports B13 (escalation/upgrades were not better; they erased savings). Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
posts 2102668315290198315 and 2103734688053448993 (@ziyacivan) -> github.com/ziyacivan/reflex-router @ 54271137 -> docs/observations.md sections dated 2026-09-22, 2026-09-23, 2026-09-24; CHANGELOG 0.3.7; README "Real-World Results" and limits -> this note. Independence: single maintainer; uses TypeSafe Jev (jev-1.13.0) as backend.
