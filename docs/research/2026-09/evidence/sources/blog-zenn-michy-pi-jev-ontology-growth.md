---
schema_version: 1
artifact_id: N-20260930-19
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105141078580199869", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:zenn.dev/michy/articles/68732e1699ca19
claim_cluster: url:zenn.dev/michy/articles/68732e1699ca19
feeds: ["memory"]
primary_source: https://zenn.dev/michy/articles/68732e1699ca19
source_commit: n/a
strength: builder-report
pillar_primary: R10
pillar_secondary: ["R9", "R5"]
memory_stage: evaluation
priority: 3
tags: {"mechanism": ["gap typing over agent traces", "noul per ontology layer", "pull request per ontology change", "human approval", "log trimming to fit the input limit"], "workload": ["data analysis agent over dbt models", "ontology as Markdown files"], "lifecycle_stage": ["evaluation", "ingestion"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium", "control": "low", "independence": "low", "reproducibility": "low", "applicability": "medium"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A System One model reading an agent's action log can indicate which layer of an ontology is thin (missing term, mapping, constraint, relation, evidence), giving a cheap signal for where to evolve the schema"]}
claim_correction: none
---

# pi x Jev: growing an ontology semi-automatically from an agent's action logs (zaiwa, Zenn)

- **URL:** https://zenn.dev/michy/articles/68732e1699ca19
- **Type:** builder writeup (Japanese)
- **Author / org:** zaiwa (Zenn account michy; self-described data scientist at a large Japanese company). X handle @Linus_lab.
- **Date:** 2026-09-30 (publishedAt 2026-09-30T12:28:42+09:00)
- **Retrieved:** 2026-09-30 (local copy of the page: repos/_src_zenn_michy.html). Read through a translating fetch; the score table and the input-limit sentence were checked in the raw page.
- **Cited by evidence:** https://x.com/Linus_lab/status/2105141078580199869 (@Linus_lab, author: says the scheme is in operation and has taken shape).
- **Relevance to a memory stack:** medium to high for the ontology priority. It is the first first-hand report found of a System One model (Jev, TypeSafe) used to decide where a knowledge schema needs to change, from the traces of an agent that works against it. It reports two sessions and no before and after result.

## TL;DR
- Three roles: Codex acts as the strategist that poses analysis questions and later drafts ontology changes; a pi agent (the minimal coding agent from badlogic/pi-mono) does the data work using only ontology tools and SQL, and logs everything; Jev reads the log and scores which ontology layer caused trouble.
- Jev answers five yes or no (`noul`) propositions, one per gap type: term, mapping, constraint, relation, evidence.
- Two sessions are shown. A thinly modelled area scores constraint 0.92, evidence 0.76, relation 0.71, term 0.61, mapping 0.19; an established area scores 0.88, 0.34, 0.17, 0.27, 0.05.
- "Semi-automatic" means drafts up to a pull request are automatic and a human approves through git review. No threshold is fixed; the author judges by feel.
- Not measured: whether the analyses were correct, and whether scores fall after an ontology change.

## What it claims / describes

**Data and ontology.** GA4 events normalised through dbt: staging; intermediate models `int_page_views`, `int_users`, `int_pages`, `int_page_releases`; marts `mart_new_users_daily`, `mart_dau_daily`, `mart_pv_daily`, `mart_recent_releases`. The ontology is a set of Markdown files with YAML frontmatter in "OKF v0.2" format. Frontmatter fields as reported: `type` (Concept, Metric or Table), `title`, `description`, `tags`, `status` (for example `draft`), followed by a Markdown body with a definition section.

**Agent tools.** The pi agent has four tools: `ontology_index`, `ontology_search`, `ontology_read`, `run_query`. Splitting the data work into pi keeps the log of one analysis separate from the wider session, so Jev receives a clean trace.

**The five gap propositions (translated).**
| Gap | Proposition given to Jev |
|---|---|
| Term gap | the agent needed a concept that the ontology does not define |
| Mapping gap | the agent was unsure how a concept maps to tables or columns and the investigation stalled |
| Constraint gap | the agent set its own conditions (period, threshold) because the ontology's conditions are vague |
| Relation gap | the agent connected concepts that the ontology does not relate |
| Evidence gap | data needed for the conclusion is absent from the logs or the dbt models |
The exact instruction and criteria text is not reproduced in the article beyond these.

**State passed to Jev.** Two keys: `trace` (the session log as readable text in time order) and `report` (the agent's final report). The article states an input limit: state plus the longest question must fit in 32k tokens, and a raw session log is about 60k tokens. A formatting script removes pi's internal metadata (ids, usage, model names), the `details` field of tool results (it duplicates the main content), the final report inside the trace, and truncates long tool results to the first 2,500 characters with a marker. Thinking, tool names and arguments, SQL, errors and agent utterances are kept.

**From score to change.**
1. Codex looks at the user's request and the Jev scores and picks areas worth improving.
2. It creates a branch per change and edits the ontology files.
3. It compares Jev scores before and after.
4. It opens a pull request; the author approves through git review.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Constraint gap | Session A 0.92; Session B 0.88 | | one session each; A is a thinly modelled area, B an established one | high in both: does not separate the two |
| Evidence gap | A 0.76; B 0.34 | | same | author ties A's value to build cost and author fields missing from `int_pages` |
| Relation gap | A 0.71; B 0.17 | | same | |
| Term gap | A 0.61; B 0.27 | | same | |
| Mapping gap | A 0.19; B 0.05 | | same | |
| Log size | about 60k tokens raw, about 32k after trimming | | one session | the 32k figure is Jev's stated input limit |
| Scores after an ontology change | not stated | | | step 3 exists in the workflow; no numbers are shown |
| Jev model version, latency, cost | not stated | | | |

## Mechanism details you could implement
- Log an agent's work against the schema (tool calls, queries, errors, reasoning) as one trace per task.
- Ask one yes or no question per schema layer about that trace, in one call, and keep the five probabilities as a gap profile for the task.
- Trim traces deterministically before scoring: drop ids and usage metadata, drop duplicated tool-result fields, cut tool outputs to a fixed length.
- Route high-gap areas to a drafting model that proposes a schema edit on a branch, and keep a human approval step.
- Planned by the author: reword questions toward observable behaviours; use a `choice` question to point at the specific file to fix; merge related changes to cut the number of pull requests.

## Limitations, caveats, counter-evidence
- Two sessions, one author, a personal project. No labels, so the scores are not validated against a judged list of real gaps.
- The constraint gap is near 0.9 in both sessions, which suggests that proposition fires regardless of ontology quality (inference).
- The author states the block on automation: the log carries no judgement of whether the analysis was good, so approval cannot be automatic; and Codex proposes too many changes, so review can back up.
- No before and after comparison is shown, so the loop is not shown to improve anything yet.
- The ontology here describes analytics concepts and tables, not product-development artifacts.
- No code repository for the author's implementation.

## Takeaways for tuning a memory stack
- A gap profile per task is a cheap, continuous signal for schema evolution that needs no labelled benchmark: it uses the traces the agents already produce.
- The five-way split (term, mapping, constraint, relation, evidence) translates to our context graph as: missing node type, weak anchoring of a claim to content, vague link conditions, missing link type, missing source.
- Check each proposition for discrimination before trusting it; one of five did not separate a thin area from a mature one here.
- Jev's input limit of 32k tokens for state plus the longest question (as stated in this article) forces trace trimming for any log-reading use.

## Open questions
- Do gap scores fall after the matching ontology edit, and does the agent's work get better? Not shown.
- How do the scores compare with a human listing the real gaps in the same sessions? Not done.
- Would the same questions work with an open-weight System One model? Not tested.

## Grading and labels
- **Directness: medium.** A first-hand description of a running system with a score table; the prompts are paraphrased and no code is released.
- **Control: low.** Two sessions, no labels, no before and after.
- **Independence: low.** Single author.
- **Reproducibility: low.** No repository for the pipeline; the pi agent and the file format are public.
- **Applicability: medium.** Schema evolution driven by agent traces is our priority 3 question; the domain differs.
- **Strength:** builder-report.
- **Pillars:** R10 primary (evolving the schema). Secondary R9 (System One model as the detector), R5 (learning from traces). Memory stage: evaluation. Priority 3; also priority 1 (a Jev usage report at a stage with no field evidence).
- **Beliefs:** none in the register are affected. Would create: trace-based gap scoring can indicate where an ontology is thin.
- **Contradiction rows:** none.

## Origin chain
- Post https://x.com/Linus_lab/status/2105141078580199869 -> https://zenn.dev/michy/articles/68732e1699ca19 -> score table (sessions A and B), input-limit paragraph, workflow list -> this note.
- Independence: single source. Uses the pi agent, which also appears in the pending cluster url:academy.dair.ai/resources/jev-decisions-in-a-pi-sdk-harness (different author; not read).
