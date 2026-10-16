---
schema_version: 1
artifact_id: N-20261001-03
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105246512481812891", "file_id": null, "sha256": null}, {"artifact_id": "post:2105246475093791179", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:suranjaychandra/jev-state
claim_cluster: github:suranjaychandra/jev-state
feeds: ["decision"]
primary_source: https://github.com/suranjaychandra/jev-state
source_commit: 3c30e8937357b946c7444d0854c5eebc7dcf234c
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4"]
tags: {"mechanism": ["state projection", "numeric banding", "relative time labels", "state pruning", "confidence threshold"], "workload": ["game NPC decisions", "synthetic scenarios"], "lifecycle_stage": ["none"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: every individual Jev answer committed in bench/results.json with per-action and per-confidence-bin tables", "control": "medium: same instructions, options and model for both arms, 3 reruns, but the policy and scenarios were written by the author for this test", "independence": "low: single author who built the library; grader is the author's rule set", "reproducibility": "high: seeded scenarios (seed 42), pinned model jev-1.13.0, npm run bench", "applicability": "medium: the failure modes (numbers read as text, counts, relative dates, irrelevant state) are exactly what memory-stage state carries; the domain is a game"}
beliefs_affected: {"supports": ["B14"], "contradicts": ["B14"], "would_create": ["Projecting raw numbers, counts and timestamps into labelled bands in code before a Jev call removes most of Jev's errors on rules that need arithmetic and cuts input tokens by about 43%"]}
claim_correction: The post's "74% to 100%" is on 70 synthetic NPC scenarios graded against the author's own rules; the README says it "does not show that Jev reasons better in general".
memory_stage: none
priority: 1
---

# jev-state: projecting raw state into labels before a Jev (TypeSafe) call, 74.3% to 100% on 70 synthetic decisions

- **URL:** https://github.com/suranjaychandra/jev-state
- **Type:** repo
- **Author / org:** suranjaychandra (Suranjay); MIT; npm `jev-state`
- **Date:** HEAD 3c30e8937357b946c7444d0854c5eebc7dcf234c, 2026-09-29 21:48:38 +0530 ("Merge pull request #5 from suranjaychandra/feat/jev-state"); benchmark run 2026-09-29 on `jev-1.13.0`
- **Retrieved:** 2026-10-01 (local shallow clone: repos/jev-state). Read: README.md, bench/results.md. Code not executed.
- **Cited by evidence:** @SuranjayK90298, 2026-09-30, https://x.com/SuranjayK90298/status/2105246512481812891 ("74% -> 100% in my benchmarks") and https://x.com/SuranjayK90298/status/2105246475093791179 ("Jev's confidence drops on raw numbers, counts and timestamps")
- **Relevance to a memory stack:** high. Our memory-stage questions (is this still true, does this supersede that, is this stale) carry timestamps, version numbers and counts; this is a controlled measurement of what pre-computing those in code buys a System One model.

## TL;DR
- The library turns raw state into labels in plain code before Jev sees it: `band` (numbers into named ranges relative to a parent value), `count` (few / several / many), `time` (epoch to "less than a minute ago"), `prune` (keep named fields, sort, cap list length), with unknown fields dropped.
- Benchmark: 70 seeded NPC scenarios, 3 reruns, 2 variants = 420 calls on `jev-1.13.0`, $0.017 total. Accuracy 74.3% raw vs 100.0% projected; answers that changed across reruns 6/70 vs 0/70; average input tokens 1,236 vs 699 (-43%); p95 latency 422 vs 390 ms.
- Errors on raw state concentrate on arithmetic rules: `retreat` 50% (compare hp to 20% of maxHp), `patrol` 43.3% (noise under a minute old), `heal` 60%.
- On raw state Jev's confidence tracked accuracy fairly well in the middle bins (0.7 to 0.9: avg confidence 81.7%, accuracy 81.4%, n=70) but was overconfident below 0.5 (41.2% vs 28.9%, n=38).
- Author's own limit: "one domain, synthetic scenarios, and a policy written for this test"; "It does not show that Jev reasons better in general."

## What it claims / describes
README lines 9 to 13 list Jev's "documented weak spots": "It reads numbers as text, so it can't compare or divide them reliably. It can't count. It struggles with mixed-format and relative dates. Its accuracy drops as irrelevant state piles up." jev-state handles those in code and "never calls the API and has no runtime dependencies". Example projection (README):

```ts
const { state } = project(gameState, {
  npc: {
    hp: band({ max: (ctx) => ctx.parent.maxHp, cuts: [0.2, 0.5], labels: ["critical", "low", "healthy"] }),
    ammo: count({ few: 5, many: 15 }),
  },
  enemies: pipe(prune({ keep: ["type", "distance"], sortBy: (a, b) => a.distance - b.distance, max: 5 }),
               each({ distance: band({ cuts: [10, 30], labels: ["near", "medium", "far"] }) })),
  lastNoiseAt: time({ now: Date.now() }),
}, { unknown: "drop" });
```

Before: "1,700 characters of positions, mesh ids, debug counters, raw numbers and epoch timestamps"; after: `{"npc": {"hp": "critical", "ammo": "several"}, "enemies": [...], "lastNoiseAt": "less than a minute ago"}`. Option helpers deduplicate labels (`_2`, `_3`) and throw on fewer than 2 or more than Jev's 255 options. A `resolve(answer, { minConfidence: 0.6 })` helper maps an answer back to the original object or null. A local playground compares raw vs projected for NPC decisions and support-ticket priority.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| accuracy | 100.0% (jev-state) | 74.3% (raw) | 70 seeded NPC scenarios x 3 reruns, jev-1.13.0 (README line 136; bench/results.md) | graded against the author's rules |
| unstable scenarios across 3 reruns | 0/70 | 6/70 | same (line 137) | |
| avg input tokens | 699 | 1,236 (-43%) | same (line 138) | |
| p50 / p95 latency | 335 / 390 ms | 336 / 422 ms | same | |
| per action, raw -> projected | retreat 50.0 -> 100; take_cover 100 -> 100; heal 60.0 -> 100; reload 90.0 -> 100; attack 86.7 -> 100; investigate 90.0 -> 100; patrol 43.3 -> 100 | | 10 scenarios per action | n=30 answers per action per arm |
| calibration bins, raw (n / avg conf / accuracy) | 0-0.5: 38 / 41.2% / 28.9%; 0.5-0.7: 32 / 58.3% / 56.3%; 0.7-0.9: 70 / 81.7% / 81.4%; 0.9-1: 70 / 95.8% / 100.0% | | 210 answers | one domain |
| calibration bins, projected | 0.5-0.7: 3 / 66.0% / 100%; 0.7-0.9: 29 / 81.3% / 100%; 0.9-1: 178 / 98.9% / 100% | | 210 answers | ceiling effect |
| total cost | $0.0171 (406,326 input tokens) | | 420 calls, 0 errors | |

## Mechanism details you could implement
- Do arithmetic, counting and date comparison in code, and send the result as a label: `hp: "critical"` rather than `hp: 38, maxHp: 250`; `lastSeen: "3 weeks ago"` rather than an epoch.
- Relative bands use a parent value (`max: ctx.parent.maxHp`), so thresholds stay meaningful across entities.
- Prune state to the fields the question needs, sorted by relevance, capped (here max 5 list items); drop unknown fields by default.
- Keep a confidence floor (`minConfidence: 0.6`) and return null below it so the caller falls back.
- For memory stages (inference): project `last_verified_at` into "verified 2 days ago / 3 months ago", version numbers into "same / older minor / older major", counts of citing artifacts into "none / one / several", before asking staleness or supersession questions.

## Limitations, caveats, counter-evidence
- One domain, synthetic scenarios, rules written by the author; projected state can encode the answer (the band named "critical" is close to the rule "retreat when hp < 20% of maxHp"), so 100% partly measures that the projection did the decision's arithmetic (README line 143 says so).
- No comparison to an LLM or to rules alone on the projected state (inference: once the state says "critical", a lookup table may also reach 100%).
- Calibration bins are small and from one domain; projected-state bins show a ceiling.
- The "documented weak spots" are cited to TypeSafe docs in the README; not re-checked here.

## Takeaways for tuning a memory stack
- Treat state projection as a required pre-step for every System One call that compares numbers, counts or dates (staleness, recency, supersession by version). It also cuts input tokens by about 40%.
- When projection makes the decision trivial, drop the model call and use the rule; keep the model for the semantic part (does this text contradict that).
- Report rerun stability (answers changing across identical calls) as a metric; it fell from 6/70 to 0/70 here.

## Open questions
- Does projection help as much on text-heavy memory decisions (contradiction, linking), where the hard part is semantic?
- How much of the gain survives when the same projected state is given to a rule or to an open-weight model (Laya, Intern-Decision)?
- Does projection change calibration in the mid range on harder tasks?

## Grading and labels
- **Directness: high.** All 420 answers committed with per-bin tables.
- **Control: medium.** Same model, instructions and options; only state differs; 3 reruns; seeded. Author-designed task.
- **Independence: low.** Library author ran and graded the benchmark.
- **Reproducibility: high.** Seed, model version and command stated.
- **Applicability: medium.** Failure modes match memory-stage state; domain does not.
- **Pillars:** R9 primary (how to make a System One model work at a stage); R4 secondary (confidence floor, error modes). **Memory stage:** none (applies to every stage that passes numeric or temporal state). **Priority:** 1.
- **Beliefs:** supports B14's decision ("fit thresholds locally; expose components"): calibration was poor below 0.5 (41.2% claimed vs 28.9% observed). Narrow contradiction row below on B14's "claimed, not shown" clause.
- **Contradiction:** B14 ("Vendor calibration is claimed, not shown"): a third-party reliability table here shows Jev's confidence matching accuracy within 2 points in the 0.5 to 0.9 bins (n=102) on one synthetic domain. This is narrow, author-graded evidence and does not overturn B14; it is the kind of local measurement B14 asks for. Open row: B14 calibration "shown" in one narrow domain, not in general.

## Origin chain
Posts @SuranjayK90298 2105246512481812891 and 2105246475093791179 (2026-09-30, replies to @polydao) -> github:suranjaychandra/jev-state at 3c30e89 -> README.md lines 9 to 13 (weak spots), 128 to 145 (benchmark, limits, calibration); bench/results.md (per-action and per-bin tables) -> this note. Independence: single author; uses TypeSafe's own SDK and model; no shared data with other bus notes.
