---
schema_version: 1
artifact_id: N-20260929-29
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104811295665279334", "file_id": null, "sha256": null}, {"artifact_id": "post:2104809800832037098", "file_id": null, "sha256": null}, {"artifact_id": "post:2104810392845496328", "file_id": null, "sha256": null}, {"artifact_id": "post:2104814523706425550", "file_id": null, "sha256": null}, {"artifact_id": "post:2104814377199395106", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:canonopylabs.com
claim_cluster: url:canonopylabs.com
feeds: ["decision"]
primary_source: https://canonopylabs.com/
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R9
pillar_secondary: ["R4", "R6"]
memory_stage: routing
priority: 2
tags: {"mechanism": ["trained-small-decision-model", "hard-rules-layer", "self-hosted-model-file", "typed-choice-questions"], "workload": ["bank-support-routing", "banking77", "game-control-doom", "game-control-snake"], "lifecycle_stage": ["routing"], "cross_cutting": ["calibration", "latency", "cost", "self-hosting", "vendor-comparison", "data-scaling"]}
evidence_grade: {"directness": "medium: vendor compares its own trained model to Jev on a named public test split and two game harnesses, but against its own written routing policy, not the Banking77 intent labels", "control": "low: Canonopy runs in-process on a laptop CPU while Jev runs over HTTPS; Jev version and prompts not stated; account states assigned at random", "independence": "low: vendor-run comparison against a competitor, promoted by an account posting in a cluster", "reproducibility": "low: dataset public (banking77 test, 3,080) but the routing policy, gold labels, training cases and Jev config are not published; no date", "applicability": "medium: shows the train-a-small-model-on-your-own-decisions option for fixed-policy routing; our memory decisions have less stable labels and longer inputs"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["On a fixed written routing policy with about 27,000 historical cases, a small trained decision model (899 KB) can beat hosted Jev few-shot (96.0% vs 86.6%, vendor-run), with accuracy falling to 78.3% at 1,000 cases"]}
claim_correction: The 12x and 1,000x figures are per-decision latency (local in-process vs Jev HTTPS round trip), not play speed; Snake ate more food (46.1 vs 40.0) but crashed more (3 vs 1 in 20 games); the 96% vs 86.6% bank result is on the vendor's own 9-action routing policy over banking77 test messages with random account states, not Banking77 intent accuracy, and "trained in a minute" is not documented for the bank model
---

# Canonopy Decisions: small trained decision models benchmarked against Jev (TypeSafe)

- **URL:** https://canonopylabs.com/ (benchmark at /#benchmark; cookbooks https://canonopylabs.com/docs/cookbooks/bank-support, https://canonopylabs.com/docs/cookbooks/doom, https://canonopylabs.com/docs/cookbooks/snake)
- **Type:** vendor blog / product site with documentation cookbooks
- **Author / org:** Canonopy (product "Canonopy Decisions"); individual authors not named
- **Date:** not stated (no benchmark date on any page read)
- **Retrieved:** 2026-09-29, live pages via WebFetch (6 fetches: home twice, /docs, bank-support, doom, snake cookbooks); no version or commit identifiers on the site
- **Cited by evidence:** @Aj_bucketshow posts https://x.com/Aj_bucketshow/status/2104811295665279334, https://x.com/Aj_bucketshow/status/2104809800832037098, https://x.com/Aj_bucketshow/status/2104810392845496328, https://x.com/Aj_bucketshow/status/2104814523706425550, https://x.com/Aj_bucketshow/status/2104814377199395106 (claims: System One model under 1 MB, trained in a minute, "faster and smarter than Jev on your specific tasks"; Doom 12 of 13 games 12x faster; Snake more food over 1,000x faster; bank messages 96% vs Jev 86.6%; $20/month)
- **Relevance to a memory stack:** medium. A concrete example of the R9 alternative to hosted Jev: train a sub-1 MB model on your own historical decisions plus hard rules, download and self-host it. Evidence is vendor-run and uncontrolled on latency.

## TL;DR
- Bank support: on the banking77 test split ("3,080 real test messages", PolyAI, CC BY 4.0), routed against "a written routing policy" (9 actions), Canonopy 96.0% (reported "96.0% ± 0.4") vs Jev few-shot 86.6% and zero-shot 83.9%; calibration error 0.006 vs 0.044 / 0.063 (metric undefined).
- Claim correction: "12x faster" (Doom, 10 ms vs 125 ms median) and "1,000x faster" (Snake, 0.08 ms in-process vs 131 ms round trip) are latency ratios, not game speed; Snake: more food (46.1 vs 40.0 per game) but more crashes (3 vs 1 of 20).
- The model is trained from history: bank model from "about 9,000 real messages, each with three account states" (about 27,000 cases); accuracy "78.3% (1,000 cases) to 96.0% (27,000 cases)". Account states "were assigned at random for the test, so real account data is still untested."
- Model size 899 KB (bank). "Trained in a minute" not documented for the bank model; Doom retraining about 20 s per cycle, Snake "a few seconds".
- $20/month per workspace, unlimited models/decisions/retraining, downloadable model files ("run it on your own servers or offline"). Model architecture not stated.

## What it claims / describes
**Product.** Canonopy Decisions is "a System One decision model API for rule-bound routing" (bank support tickets, complaint triage, content moderation). Workflow per "How it works": describe rules, confirm examples, deploy. Models answer typed choice questions over a state schema, with hard rules that cannot be broken ("The bot can't promise a refund your rules don't allow"). Positioning with LLMs: "Let the LLM talk. Let your model decide. ... Your model picks the action; your LLM writes the reply around it." Docs include a "Coming from Jev" page (/docs/day-one), confidence and "running it yourself" pages, and an MCP server so coding agents can read the docs (not fetched).

**Bank support benchmark.** Test: banking77 test split, 3,080 messages. Target: one of 9 actions (home page: "9 next steps under five hard rules"; cookbook: "9 state fields and 3 rules that can't be broken"; the rule count is inconsistent between pages). Training: about 27,000 cases from about 9,000 real messages x 3 account states (inference: the banking77 train split has 10,003 messages, so "about 9,000" is a subset or after filtering; not stated). Gold labels are "against a written routing policy"; who wrote the policy and who labelled the 3,080 test messages is not stated, nor whether an LLM helped. The site notes "either model may have seen it before" (banking77 is public) and that "some of Jev's misses were defensible calls, and counting those as right the lead is still about 5-7 points". Jev arms: few-shot and zero-shot, "over HTTPS at list price"; Jev version, prompts and questions not stated. Canonopy timing "Measured on a laptop CPU".

**Doom benchmark.** Model `doom-4`, 13 live games on Freedoom MAP01, "the same 13 live games for every side, on the same map, with the same state, the same four questions and the same controller." Four choice questions per tick (move, look direction, fire, door). Hard rules on firing (ammo, enemy alignment, range). State schema of 74 fields. Trained on 18,237 recorded moments over four iterations fixing observed failures (wall-bumping, unreachable targets, post-combat staring); about 20 s per retrain; held-back accuracy 97.2 to 100% across the four questions. Caveats on the page: latency favours local deployment, small sample, Jev varies (26 to 34 kills across runs), and spawning caps kills at about four on this map.

**Snake benchmark.** 20 games on a 16x16 board against Jev's default "safe" strategy, stopped after about 700 moves. Model trained on 3,000 moves from "a simple scripted player" in "a few seconds", 99% agreement with the recorded player on held-back moves. Jev comparison "used the demo's own code and engine". A second build from the same data got 44.9 food and 5 crashes.

## Numbers

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Routing accuracy (bank) | 96.0% ("96.0% ± 0.4") | Jev few-shot 86.6%; Jev zero-shot 83.9% | banking77 test, 3,080 messages, 9-action written policy | vendor gold labels, labeller not stated; random account states; Jev version not stated |
| Lead if Jev's "defensible" misses counted right | "about 5-7 points" | | same | vendor judgement of defensibility |
| Calibration error (bank) | 0.006 | Jev few-shot 0.044; zero-shot 0.063 | same | metric not defined |
| Time per decision p50 (bank) | 38.9 ms | Jev few-shot 177 ms; zero-shot 216 ms | Canonopy on laptop CPU; Jev over HTTPS | unmatched conditions |
| Cost per million decisions (bank) | $0.78 | Jev few-shot $158.61; zero-shot $55.58 | Jev at list price | Canonopy compute basis not stated beyond self-hosted |
| Accuracy vs training history (bank) | 78.3% at 1,000 cases; 96.0% at 27,000 cases | | same test | intermediate points not captured |
| Model size (bank) | 899 KB | | | architecture not stated |
| Doom games won | 12 of 13 | Jev 1 | 13 live games, Freedoom MAP01 | small n; kills capped by spawns |
| Doom kills / deaths | 56 / 0 | Jev 34 / 6 | same | Jev 26 to 34 kills across runs |
| Doom map squares explored | 282 | Jev 114 | same | |
| Doom median response time | 10 ms | Jev 125 ms | same | this is the "12x" (inference: 12.5x) |
| Doom held-back accuracy | 97.2 to 100% | | 4 questions, 18,237 recorded moments | agreement with training source, not play quality |
| Snake food per game | 46.1 | Jev 40.0 | 20 games, 16x16, about 700 moves cap | second build 44.9 |
| Snake crashes | 3 of 20 | Jev 1 of 20 | same | second build 5 crashes |
| Snake decision latency | 0.08 ms in-process | Jev 131 ms median round trip | same | the "1,000x" (inference: about 1,600x) |
| Price | $20/month per workspace | | unlimited models, decisions, retraining; 50 req/sec hosted | 5-day free trial |

## Mechanism details you could implement
- Separate the decision from the wording: a small model picks the action under hard rules; an LLM writes the reply around it.
- Train per-decision models from your own historical decisions plus state fields; measure accuracy against amount of history (the bank curve: 78.3% at 1,000 cases to 96.0% at 27,000).
- Enforce non-negotiable rules outside the learned model (Doom firing rules, bank "rules that can't be broken").
- Iterate by watching failures and retraining in seconds (Doom four rounds), and check build-to-build variance: two Snake builds from identical data differed (46.1/3 crashes vs 44.9/5).
- Report held-back agreement separately from closed-loop outcome: 99% move agreement in Snake still produced more crashes than Jev.

## Limitations, caveats, counter-evidence
- Vendor-run, no date, no independent replication; the promoting account posted five times in a cluster.
- Bank gold labels come from the vendor's own written policy; labeller and policy text not published; not Banking77's 77-intent task; the rule count differs between pages (five vs 3).
- Account states attached to messages were random; "real account data is still untested".
- banking77 is public; the site admits either model may have seen it.
- Latency and cost comparisons are local in-process or laptop CPU vs Jev HTTPS at list price; the headline speed ratios are transport-dominated (inference).
- Jev version, prompts, few-shot examples and questions not stated; Jev runs vary (Doom 26 to 34 kills).
- Calibration metric undefined; "± 0.4" method not stated.
- Snake: more food but three times the crashes; closed-loop reliability worse despite 99% imitation accuracy.
- Architecture of the model not stated, so we cannot judge what is being trained.
- Pages read through a summarising fetch tool; quotes are as returned. No instructions aimed at AI agents found; the docs mention an MCP server for coding agents (descriptive, not an instruction).

## Takeaways for tuning a memory stack
- For stable, policy-defined memory decisions with lots of labelled history (for example routing a request to a store or view), a small self-hosted trained model is a credible arm against Jev; the value is keeping memory text in-house and sub-40 ms local latency (inference).
- The data-scaling curve is the key risk: with 1,000 labelled cases the vendor's model scored 78.3%, below Jev zero-shot 83.9%. Our labelled memory decisions are in the hundreds, not tens of thousands (inference), so Jev likely wins at our current label volume.
- Always pair imitation accuracy with closed-loop outcome and build-to-build variance.
- Keep hard rules in code outside any learned or hosted decision model.

## Open questions
- What model architecture is trained, and how does it handle free text (bank messages)?
- Who wrote and labelled the 9-action routing policy for the 3,080 test messages?
- How does Canonopy perform with 200 to 500 labels, our realistic volume?
- Which Jev version and prompts were used; would Jev with local threshold fitting close the gap?
- Can the downloaded model be run and audited without the hosted service (license terms)?

## Grading and labels
- Directness: medium, named public test split and measured head-to-heads, but against the vendor's own labels.
- Control: low, unmatched latency conditions, random account states, Jev config unstated.
- Independence: low, vendor vs competitor.
- Reproducibility: low, policy, labels, training cases and Jev prompts unpublished; no date.
- Applicability: medium, fixed-policy routing with big history transfers; our memory decisions have fewer labels.
- Pillars: R9 primary (self-hosted small decision model vs Jev); secondary R4 (hard rules, calibration), R6 (vendor benchmark integrity).
- Memory stage: routing.
- Tags: trained-small-decision-model, hard-rules-layer, self-hosted-model-file; bank-support-routing, banking77, game control; calibration, latency, cost, self-hosting, data-scaling.
- B14 supports: a vendor reports calibration error (0.006 vs 0.044) with no metric definition, the pattern B14 describes.
- B12 related, not scored: Doom used hard rules and a shared controller; Snake crashed more in open loop despite 99% imitation (consistent with B12's caution, different setup).
- Would create: small trained model beats Jev few-shot on a fixed policy at 27,000 cases, loses ground at 1,000 cases (vendor-run).

## Origin chain
- @Aj_bucketshow posts (5) -> https://canonopylabs.com/ benchmark table (/#benchmark) -> bank numbers; -> /docs/cookbooks/bank-support -> training history and data-scaling; -> /docs/cookbooks/doom -> Doom table; -> /docs/cookbooks/snake -> Snake results; -> /docs -> pricing, downloadable models.
- Independence: all numbers are from the vendor's own site; the posts restate them with latency ratios presented as general speed. No third-party replication found.
