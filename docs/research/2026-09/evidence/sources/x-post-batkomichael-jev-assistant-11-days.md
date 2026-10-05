---
schema_version: 1
artifact_id: N-20260930-22
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105121047196672041", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x:2105121047196672041
claim_cluster: x:2105121047196672041
feeds: ["decision"]
primary_source: https://x.com/batkomichael/status/2105121047196672041
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R3", "R4"]
memory_stage: assembly
priority: 1
tags: {"mechanism": ["tool-output filtering", "verbatim trimming instead of summarising", "playbook selection (skill plus memory)", "model routing", "done-claim check"], "workload": ["personal agent harness on Fable and Opus", "meeting follow-up, email, investigation"], "lifecycle_stage": ["assembly", "routing", "recall_gate"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "low", "control": "low", "independence": "low", "reproducibility": "low", "applicability": "medium"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A fast decision model checking a done claim before it is accepted catches a measurable stream of premature completions (52 in 3 days in one user's harness)"]}
claim_correction: none
---

# "I gave my expensive AI a cheap, fast assistant: 11 days in" (@batkomichael): Jev (TypeSafe) at five points in a personal agent harness

- **URL:** https://x.com/batkomichael/status/2105121047196672041
- **Type:** X post (first-hand usage report; the author says the text is a summary written by his Claude)
- **Author / org:** @batkomichael (individual builder)
- **Date:** 2026-09-30; covers use since 2026-09-19
- **Retrieved:** 2026-09-30 from the staged item record (full post text). No linked repository, article or log. The post is the whole source.
- **Cited by evidence:** the post itself; selected by the decision digest of 2026-09-30 (lead item: "52 false done claims blocked in three days").
- **Relevance to a memory stack:** medium. A priority 1 usage report: a named builder, a running system, and counts. It places a System One model at context assembly (filtering and trimming), at playbook selection (which skill and memory to load), at model routing and at a completion check. Nothing is measured against a baseline.

## TL;DR
- Setup: "Fable/Opus do the thinking. Jev (TypeSafe's model) makes the small calls in ~0.3s each, for about a hundredth of a cent a call."
- Five uses: filter tool output to the relevant pages; trim long chats word for word instead of summarising; pick the playbook (skill plus memory) before work starts; send routine work to Haiku instead of Opus; ask "did you actually check?" before a "done" is accepted.
- Since 19 Sep: "142 sessions, 5,061 decisions, no outages".
- "33 trims, context ~66% smaller each time"; "52 premature 'done's blocked in 3 days"; "Right playbook pulled 192 times"; "~238M token reads avoided by 28 Sep (~19%, estimate), mostly from compaction".
- Counts only. No accuracy, no false-block rate, no comparison arm.

## What it claims / describes

The five decision points, verbatim from the post:
- "Filters tool output: gives the model only the relevant pages, sets the rest aside (nothing lost)"
- "Trims long chats word for word instead of turning them into a vague summary"
- "Picks the right playbook (skill + memory) before work starts"
- "Sends grunt work to the cheap model (Haiku) instead of Opus"
- "Asks 'did you actually check?' before letting a 'done' through"

How each decision is posed to Jev (question type, options, thresholds) is not stated. Whether the set-aside tool output is stored and how it is recovered is not stated beyond "nothing lost". What "right playbook" was judged against is not stated.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Sessions and decisions | 142 sessions, 5,061 decisions, no outages | | 19 Sep to 30 Sep 2026, one user | self-reported, summarised by an assistant |
| Latency and cost per decision | about 0.3 s; "about a hundredth of a cent a call" | | | approximate |
| Context trims | 33 trims, context about 66% smaller each time | "built-in version fired 3x in the previous 90 days" | same harness | different trigger rules, so not a like-for-like comparison (inference) |
| Premature completion claims blocked | 52 in 3 days: 33 "here's what I'll do" instead of doing it, 19 "tests pass" with nothing run | | | no count of wrongly blocked correct claims |
| Playbook selections | 192 (meeting follow-up 36, email 34, investigate 32) | | | "right" is the author's word; not verified |
| Token reads avoided | about 238M by 28 Sep, about 19%, "estimate", "mostly from compaction" | | | estimation method not stated |
| Accuracy of any of the five decisions | not stated | | | |

## Mechanism details you could implement
- Context assembly: have a fast decision model select which pages of a large tool result go to the main model and park the rest for retrieval on demand.
- Compaction: select which earlier turns to keep verbatim rather than rewriting them. This matches the truncate-not-rewrite result in note paper-cliffcompaction-truncate-not-rewrite-2609-26779.md.
- Recall gate and routing: choose one playbook (a skill and its memory) before the task starts, from a fixed list.
- Completion check: before accepting a "done", ask whether the claimed check was actually performed; the two failure shapes reported are a plan presented as a result and a test claim with no test run.

## Limitations, caveats, counter-evidence
- A single user's harness and a single post; the text is an assistant-written summary of the author's logs.
- No false-positive side: a blocked "done" that was in fact correct would cost a turn; the rate is unknown.
- "Nothing lost" for set-aside tool output is asserted, not shown.
- The saving is attributed "mostly" to compaction, which a rule could also trigger; the share owed to the decision model is unknown (inference).
- No code, no configuration.

## Takeaways for tuning a memory stack
- The completion check is the use with the clearest count and the most direct parallel to our "check before an agent acts" item: a cheap yes or no on whether claimed evidence exists.
- Playbook selection is a recall-gate decision (which memory to load at all) made once per task from a closed list; it is a small, testable slice.
- Treat the token saving as a lead, not a result.

## Open questions
- How often does the completion check block a correct claim? Not stated.
- How is a parked page of tool output recovered when it turns out to be needed? Not stated.
- What are the Jev questions and thresholds? Not stated.

## Grading and labels
- **Directness: low.** Counts from a self-report; no artifacts.
- **Control: low.** No baseline except a loose comparison with a built-in compaction trigger.
- **Independence: low.** One user, one system.
- **Reproducibility: low.** Nothing released.
- **Applicability: medium.** An agent harness doing knowledge work with skills and memory; decisions at stages we care about.
- **Strength:** builder-report.
- **Pillars:** R9 primary (where a System One model sits and what it did). Secondary R3 (context assembly), R4 (automating a completion check). Memory stage: assembly. Priority 1. Written as a priority usage note (credible first-hand report, no test implied).
- **Beliefs:**
  - B9 adjacent: large token reductions are reported, but at unknown accuracy.
  - Would create: a fast completion check catches a steady stream of premature done claims.
- **Contradiction rows:** none.

## Origin chain
- Post https://x.com/batkomichael/status/2105121047196672041 (the full claim is in the post) -> this note. No paper, repository or article behind it.
- Independence: single source. Overlaps in mechanism with JevScout (note github-yctimlin-jevscout.md, tool-result condensing with Jev) and CliffCompaction; no shared code or data.
