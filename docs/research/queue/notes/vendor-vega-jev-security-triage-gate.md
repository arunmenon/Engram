---
schema_version: 1
artifact_id: N-20261008-02
artifact_type: note
producer: triage
run_id: triage-20261008T014615Z-49b5
created_at: 2026-10-08T01:58:00Z
input_refs: [{"artifact_id": "post:2105226177660993616", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:vega.io/blog/jev-closed-up-to-a-third-of-our-triage-agents-alerts
claim_cluster: url:vega.io/blog/jev-closed-up-to-a-third-of-our-triage-agents-alerts
feeds: ["memory", "decision"]
primary_source: https://vega.io/blog/jev-closed-up-to-a-third-of-our-triage-agents-alerts
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R9
pillar_secondary: ["R4"]
memory_stage: routing
priority: 1
tags: {"mechanism": ["one-sided confidence gate", "typed questions from playbook", "pre-agent filter"], "workload": ["security alert triage", "agent loop"], "lifecycle_stage": ["routing"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: vendor write-up with per-tenant figures, raw data not released", "control": "medium: agent baseline on the same replayed alerts, threshold picked on one tenant and held fixed on the other", "independence": "low: Vega runs the agent and the study; judges are one LLM family", "reproducibility": "low: private tenant data, offline replay only", "applicability": "medium: same shape as a pre-agent gate on our memory stages, different domain"}
beliefs_affected: {"supports": ["B12", "B14"], "contradicts": [], "would_create": ["A one-sided Jev gate in front of an LLM agent can close 15 to 33% of cases at about 98% correct, while Jev deciding outright loses to the agent"]}
claim_correction: Post says "about a third of alerts cleared ... right 98%"; the source shows 33% on the quiet tenant and 15% on the busy one at threshold 0.8, judged by LLM runs plus analyst correction, in an offline replay that "has not run on a live alert". The post's Vercel ~13% figure is not in this source.
---

# Vega put Jev (TypeSafe) in front of its security triage agent: 15 to 33% of alerts closed at 98 to 99% right, offline replay

- **URL:** https://vega.io/blog/jev-closed-up-to-a-third-of-our-triage-agents-alerts
- **Type:** vendor blog
- **Author / org:** Ido Kuks, Vega
- **Date:** 21 Sept 2026 (page byline)
- **Retrieved:** 2026-10-08 via WebFetch (extract quoted below; quotes are from the fetched page as returned by the fetch tool)
- **Cited by evidence:** @Tal_Weiss7, https://x.com/Tal_Weiss7/status/2105226177660993616 (2026-09-30, video, second-hand)
- **Relevance to a memory stack:** medium-high. It is a first-hand usage report of Jev as a gate before an LLM agent (priority 1), with a threshold, an agent baseline and false-negative counts: the same pattern as a recall gate or write gate in front of an LLM.

## TL;DR
- Vega generated Jev questions from its triage playbook (one Choice ESCALATED / NOT_ESCALATED / MISSING_DATA_SIGNALS, one Choice for benign explanation, "fifteen Nouls straight from the playbook") and used Jev as a one-sided gate: close an alert only when Jev says "not escalated" at 0.8 or above; everything else goes to the agent.
- At 0.8: closed 15% (busy tenant) and 33% (quiet tenant), right 98% and 99% per the judges; confirmed escalations wrongly closed: one (busy) and two (quiet). At 0.9: 8% and 20% closed, 98 to 100% right.
- Speed "230 times faster" (one Jev call, about half a second, vs the agent's median two minutes and four to five model calls); cost "2,000 times cheaper", about a hundredth of a cent per alert vs $0.34 average for the agent.
- Claim correction: "about a third" is only the quiet tenant; the result is an offline replay ("None of it has run on a live alert"); the 98% is judged by three runs of Claude Fable 5.1 with analyst verification. Jev deciding outright "loses to the agent on both tenants".

## What it claims / describes
The triage agent runs "in a loop": "two minutes per alert at the median and $0.34 on average, four to five model calls and one round of online queries" (LLM not stated). Jev is described as "not an LLM and it does not generate text", answering Choice, Noul and Score questions. Questions were generated from the playbook, for example "Did the flagged action actually complete or succeed?" and "Is there enough evidence in the state to make a confident call without further investigation?". Data: "Two tenants, three weeks of their agents' alerts, replayed"; busy tenant "hundreds of alerts ... about half escalated"; quiet tenant "about half as many alerts, and the agent escalated one in six". Ground truth: three runs of Claude Fable 5.1 as judges over "more than half of the agent's alerts on each tenant"; analysts "verified the labels and corrected them where the judges were wrong". The threshold 0.8 was chosen on the busy tenant and not adjusted for the quiet one. Next step stated: "The first thing going in is the one-sided gate with the tenant context in front of the agent."

## Numbers

| Metric | Value | Baseline | Setup (n) | Caveat |
|---|---|---|---|---|
| Alerts closed by Jev gate @0.8 | busy 15%, quiet 33% | agent decides all | two tenants, three weeks replayed, n "hundreds" (exact n not stated) | offline |
| Right per judges @0.8 | busy 98%, quiet 99% | agent's own verdicts: 72% (busy), 75% (quiet) right per judges | closed alerts only | judge is one model family |
| Confirmed escalations wrongly closed @0.8 | busy 1, quiet 2 | | | denominators not stated |
| Gate @0.9 | closed 8% / 20%, 98 to 100% right | | | |
| Speed | 230x faster; Jev ~0.5 s | agent median two minutes | | per-alert |
| Cost | 2,000x cheaper; ~0.01 cent per alert; both replays under $1 Jev credits | agent $0.34 average | | |
| Jev deciding outright | loses to the agent on both tenants | agent | | figure not extracted |

## Mechanism details you could implement
- One-sided gate: act only on the cheap model's confident "safe" side (not escalated >= 0.8); send everything else to the expensive path. Fit the threshold on one population and check transfer on another.
- Generate typed questions mechanically from an existing playbook or rubric (one Choice for the verdict, one for the explanation, nouls for each playbook check).
- Keep state short: "More text is less signal for a model that reads the state once and picks"; state cap "around 32k tokens".

## Limitations, caveats, counter-evidence
- Offline replay, two tenants, private data; "the threshold would need picking again on live data".
- Jev is "bad at comparing numbers, negations confuse it, it reads literally".
- Judges: three runs of one LLM (Claude Fable 5.1) plus analyst correction; the agent's LLM is not stated, so judge-agent model overlap is unknown.
- Fetched through a summarising fetch tool; exact table layout and n not captured (inference: re-read the page before citing numbers externally).
- The X post's Vercel "~13% of paid AI Gateway teams on day one" is not in this source; it stays unsourced.

## Takeaways for tuning a memory stack
- Use Jev as a one-sided pre-filter in front of the LLM path (for example "no recall needed" or "skip write"), not as the sole decider.
- Report false negatives on the closed side as counts, and fit the threshold on one corpus, test on another.

## Open questions
- Exact n per tenant and the share of judge labels changed by analysts?
- Does the gate hold on live traffic?

## Grading and labels
- Directness medium; control medium (agent baseline, held-fixed threshold); independence low; reproducibility low; applicability medium.
- R9 primary (Jev at a gate stage), R4 secondary (when to automate). Memory stage: routing (gate before the agent). Priority 1.
- B12 supports: Jev alone loses to the agent; under the agent as a one-sided gate it adds value. B14 supports: threshold fitted locally per tenant, not vendor calibration.
- No contradiction rows.

## Origin chain
post x:2105226177660993616 (@Tal_Weiss7, video, no link) -> vega.io/blog index -> the Vega post (21 Sept 2026, Ido Kuks) -> sections on setup, numbers and limits as extracted -> this note. Independence: single organisation runs agent, data and evaluation; judges Claude Fable 5.1.
