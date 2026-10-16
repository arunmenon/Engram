---
schema_version: 1
artifact_id: N-20260929-11
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104599104538194043", "file_id": null, "sha256": null}, {"artifact_id": "post:2104599799647646050", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:23blocks-os/ai-maestro
claim_cluster: github:23blocks-os/ai-maestro
feeds: ["memory", "decision"]
primary_source: https://github.com/23blocks-OS/ai-maestro
source_commit: b2e192837ce4c8b5d3fe696e01b43f94ceccbbd6
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R2", "R10"]
memory_stage: write_gate
priority: 1
tags: {"mechanism": ["jev-noul-durable", "jev-choice-category", "jev-score-importance", "correction-detection", "verbatim-passage-storage", "relation-classification", "reinforcement-dedupe"], "workload": ["coding-agent-conversations", "multi-agent-fleet"], "lifecycle_stage": ["write", "linking", "consolidation"], "cross_cutting": ["provider-fallback", "unmeasured"]}
evidence_grade: {"directness": "medium: the write gate code is read directly, but there is no measurement of its decisions", "control": "unknown: no evaluation exists (backlog F007 is Todo)", "independence": "low: the two posts come from the project org and its maintainer", "reproducibility": "high: code pinned at a commit with defaults in lib/memory/settings.ts", "applicability": "high: coding-agent conversations promoted to long-term memory, the same write-gate problem as ours"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": []}
claim_correction: The posts describe a Jev memory gate that evaluates conversations; the gate exists in code (durable noul >= 0.75, category not none, importance >= 2.5 of 0-4, corrections admitted at durable >= 0.5), but no evaluation of its decisions exists, and the repo's own backlog item F007 says nothing yet measures whether recalled memory is used.
---

# AI Maestro memory: a Jev write gate that promotes coding-agent conversation passages to long-term memory

- **URL:** https://github.com/23blocks-OS/ai-maestro
- **Type:** repo
- **Author / org:** 23blocks-OS (23blocks); head commit authored by Juan Pelaez with Claude Opus 5.5 as co-author
- **Date:** head commit `b2e192837ce4c8b5d3fe696e01b43f94ceccbbd6` (2026-09-25T18:41:33Z, "docs: agentlog vs AMP; backlog F015 AMP topics with replayable offsets (v0.45.7) (#511)")
- **Retrieved:** 2026-09-29, commit b2e192837ce4c8b5d3fe696e01b43f94ceccbbd6 (SHA from GitHub commits API; no local clone, shell unavailable). Read: lib/memory/jev-provider.ts, lib/memory/consolidate.ts, lib/memory/settings.ts, app/api/agents/[id]/memory/consolidate/route.ts, backlog/F007-measure-memory-use.md, and directory listings of lib/ and lib/memory/. Not read: lib/memory/skill.ts, recall/search/dedupe/cards code, CLAUDE.md. Line numbers are omitted because the fetch tool reported inconsistent numbers across passes; locators are file and symbol names.
- **Cited by evidence:** https://x.com/23blocks_co/status/2104599104538194043 (@23blocks_co: "memory skill of AI Maestro. It evals conversations and use Jev ... to classify and move to long term memories"); https://x.com/jkpelaez/status/2104599799647646050 (@jkpelaez: "Memory gate implementation with Jev", link target is a t.co URL, not resolved; @jkpelaez is likely maintainer Juan Pelaez, inference)
- **Relevance to a memory stack:** medium-high for priority 1 (write_gate). A second concrete Jev write gate, alongside jevmem, with different design choices (verbatim passages, higher durable threshold, corrections path, provider fallback), but no measurement.

## TL;DR
- Consolidation classifies conversation passages with Jev (`POST {url}/v1/systemone`, default `https://api.typesafe.ai`, `jev-latest`) using three questions: `durable` noul, `category` choice (fact, decision, preference, pattern, insight, reasoning, none), `importance` score (Irrelevant, Minor, Useful, Important, Critical).
- Accept rule (`accepts` in JevClassifier): `if (this.isCorrection(c) && c.durable >= 0.5) return true; return c.category !== 'none' && c.durable >= this.settings.minDurable && c.importance >= this.settings.minImportance`, defaults `minDurable: 0.75`, `minImportance: 2.5` ("0-4 rubric"); correction = separate noul, `MIN_CORRECTION = 0.75`.
- Passages are stored verbatim (no LLM rewriting); dedupe at similarity 0.85+ reinforces an existing memory instead of creating one; relations (supports, contradicts, supersedes, leads_to) classified with default `minConfidence = 0.6`, supports 0.8.
- Provider "auto" order: Jev if a key is configured, else Ollama, else Claude.
- No eval: backlog F007 (Todo) says "Nothing yet says whether the agent used it." Claim correction: a concrete gate, not a measured one.

## What it claims / describes
- **Where it runs.** `services/agents-memory-service` exposes `triggerConsolidation`, `getConsolidationStatus`, `manageConsolidation` via `app/api/agents/[id]/memory/consolidate/route.ts` (GET, POST, PATCH; dry-run, provider selection, conversation limits). `lib/memory/consolidate.ts` header: "Core logic for extracting long-term memories from conversations. Handles deduplication, reinforcement, and relationship building." Selects conversations with unconsolidated messages, default `maxConversations` 50 per run.
- **Classifier** (`lib/memory/jev-provider.ts`, header "Jev classifier provider (TypeSafe System One model, or any compatible API)"): classifies passage worth-ness rather than generating text; request `{ model, state, questions } -> { answers }`.
- **Questions:**
  - `durable` (noul): "Would an engineer working on this project in a future session benefit from remembering this passage?" True: "Contains a lasting decision, fact, preference, pattern, insight or rationale about the project, codebase, user or workflow". False: "Transient: status chatter, tool output, one-off debugging steps, pleasantries, or nothing reusable".
  - `category` (choice): fact, decision, preference, pattern, insight, reasoning, none (each with criteria; full criteria text not captured).
  - `importance` (score): five levels Irrelevant, Minor, Useful, Important, Critical.
  - Correction (noul): "is the user correcting the assistant: saying that something the assistant did, said, assumed or proposed was wrong, or telling it to do it differently?"; `MIN_CORRECTION = 0.75`.
- **Passage constants:** `MAX_PASSAGE_CHARS = 2000`, `MAX_EXCHANGE_CHARS = 12000`, `MAX_CONTEXT_CHARS = 600`, `MIN_USER_PASSAGE_CHARS = 40`, `MIN_ASSISTANT_PASSAGE_CHARS = 120`, `MAX_CONCURRENT = 8`. Classification output `ChunkClassification`: durable, category, categoryConfidence, importance, correction (optional), model, inputTokens.
- **Linking:** `classifyRelations` over memory pairs: supports, contradicts, supersedes, leads_to; `SUPPORTS_MIN_CONFIDENCE = 0.8`, default `minConfidence = 0.6`. `classifyEntityRelations` with `ENTITY_PREDICATES`, default `minConfidence = 0.7`. Candidate pairs within cosine distance `LINK_MAX_DISTANCE = 0.35` (consolidate.ts).
- **Consolidate.ts constants:** `MIN_FAITHFULNESS = 0.6` ("Min P(card statement supported by evidence)", for summary cards; which model answers it is not confirmed), `MAX_PASSAGES_PER_RUN = 1000`, `MAX_SUMMARY_CALLS_PER_RUN = 10`, dedupe similarity 0.85+ reinforces.
- **Long-term record fields:** memory_id, agent_id, tier, system, category, content, context, source_conversations, confidence, reinforcement_count, created_at.
- **Lifecycle:** warm memories promote to a "recurring" tier when age >= `minAgeDays` and `reinforcement_count` >= `minReinforcements` (defaults not found in settings.ts); short-term messages older than `retentionDays` are pruned from consolidated conversations.
- **Logging:** `[CONSOLIDATE]` log lines for provider choice, dedupe decisions, creation and reinforcement, card rejection reasons, corrections, lifecycle transitions. No decision log with per-question probabilities was seen (jevmem keeps one).

## Numbers

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| any accuracy, precision or recall of the gate | not stated | | none | F007 status "Todo": "Nothing yet says whether the agent used it." |
| thresholds (config) | minDurable 0.75; minImportance 2.5 (0-4); MIN_CORRECTION 0.75; correction durable floor 0.5 | jevmem: contentMin 0.5, round(importance) >= useful | lib/memory/settings.ts, jev-provider.ts | no stated rationale for values |
| linking thresholds | minConfidence 0.6; supports 0.8; entity 0.7; LINK_MAX_DISTANCE 0.35 | jevmem contradiction 0.7 plus named target | jev-provider.ts, consolidate.ts | |

## Mechanism details you could implement
- Gate as code over three typed answers: `category != none AND P(durable) >= 0.75 AND importance >= 2.5`, plus a correction bypass (`P(correction) >= 0.75 AND P(durable) >= 0.5`). User corrections are treated as high-value memories with a lower durable bar.
- Store the verbatim passage (bounded 40 to 2,000 chars; context 600 chars) instead of an LLM rewrite; jevmem instead rewrites to one line of at most 200 chars with a small LLM.
- Reinforce on near-duplicate (similarity 0.85+) and use `reinforcement_count` plus age to promote tiers; a reinforcement-based promotion rule rather than decay.
- Typed relation classification at write time (supports, contradicts, supersedes, leads_to) over embedding-near pairs (cosine distance <= 0.35).
- Provider fallback chain Jev -> Ollama -> Claude, keeping memory text local when no Jev key is set.

## Limitations, caveats, counter-evidence
- No measurement of gate quality, recall use, or memory growth. F007 planned: "recalled N times, used M", per-agent use rate, a Jev call per injection to judge use.
- Thresholds are fixed defaults with no fitting on labels (contrast jevmem `fit` on >= 40 labels; B14 says fit locally).
- Differences vs jevmem: no poisoning/injection question in the gate (none seen in the files read), no supersession tag handling seen, no borderline escalation tier. Whether recall frames memories as "facts, not instructions" is not known (recall code not read).
- `importance >= 2.5` presumably compares an expected score on 0-4, which sits between Useful (2) and Important (3), stricter than jevmem's round >= Useful (inference).
- Verbatim storage of assistant passages of up to 2,000 chars could admit tool output or instructions if the durable noul misfires (inference).

## Takeaways for tuning a memory stack
- Two independent Jev write gates now converge on the same shape: a durable/content noul, a kind choice with `none`, a 5-level importance score, thresholds in config. Their thresholds differ (0.75 and 2.5 here vs 0.5 and round >= 2 in jevmem), which is itself a reason to fit thresholds on our own labels rather than copy either.
- The correction bypass is worth an arm: user corrections of the agent are likely the highest-value memories for coding agents (inference).
- Add the injection question at the gate (jevmem, B24) if adopting this design.

## Open questions
- Category criteria text and the importance level descriptions in full.
- Defaults for minAgeDays, minReinforcements, retentionDays (not in settings.ts).
- Fleet-level admission rate: what fraction of passages pass?
- Whether F007 results will be published.

## Grading and labels
- Directness: medium, code read, no outcomes.
- Control: unknown, no eval.
- Independence: low, both posts from the maintainers.
- Reproducibility: high, pinned commit and defaults.
- Applicability: high, coding-agent conversation memory.
- Strength: repo-pinned.
- Pillars: R9 primary; R2, R10 secondary (relation types).
- Memory stage: write_gate.
- Tags: jev-noul-durable, jev-choice-category, jev-score-importance, correction-detection, verbatim-passage-storage; unmeasured.
- Beliefs: none supported or contradicted (no measurement); relevant context for B13, B14, B24 comparisons only.

## Origin chain
- post https://x.com/23blocks_co/status/2104599104538194043 and https://x.com/jkpelaez/status/2104599799647646050 -> https://github.com/23blocks-OS/ai-maestro @ b2e192837ce4c8b5d3fe696e01b43f94ceccbbd6 -> lib/memory/jev-provider.ts (MEMORY questions, CORRECTION_QUESTION, accepts, classifyRelations), lib/memory/settings.ts (DEFAULT_CLASSIFIER_SETTINGS), lib/memory/consolidate.ts (provider choice, thresholds, schema, promotion, pruning), backlog/F007-measure-memory-use.md.
- Independence: both posts are from the project (org account and, likely, its maintainer); not independent of each other. Comparison baseline: jevmem note (context/example-note.md).
- The repo contains agent instruction files (CLAUDE.md, .agents/skills/, .claude/skills/) aimed at coding agents working on the repo; not read and not followed.
