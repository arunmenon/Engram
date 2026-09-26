# Hippo (hippo-memory): biologically-inspired memory layer for AI agents

- **URL:** https://github.com/kitfunso/hippo-memory
- **Type:** repo
- **Author / org:** kitfunso (maintainer referred to as "Keith" in docs/evals); MIT license; npm package `hippo-memory`
- **Date:** commit read `d4e163339d1e0a842caa759eadda6cce5161771b` (committed 2026-09-25 17:04 +0100). Schema version 46 (`src/db.ts: CURRENT_SCHEMA_VERSION = 46`).
- **Retrieved:** 2026-09-26 (local copy: /private/tmp/claude-501/-Users-arunmenon-projects-localai-signals/3f9824a6-23ac-471e-adc7-a1ca0ec806fd/scratchpad/repos/hippo-memory, shallow clone)
- **Cited by evidence:** Memory that updates on read / 2026-09-24 sergeonsamui (claim: "decay, retrieval strengthening and consolidation; LongMemEval R@5 = 74% with BM25 only")
- **Relevance to a memory stack:** high. Complete, readable implementation of read-time strengthening, outcome-weighted decay, supersession and sleep consolidation, plus unusually honest pre-registered ablations that say which of those mechanisms actually help.

## TL;DR
- Local-first TypeScript memory layer: SQLite (`.hippo/hippo.db`) with markdown mirrors, zero runtime deps, Node 22.16+, CLI + MCP (stdio, 13 tools) + HTTP API, hooks for Claude Code, Codex, Cursor, OpenClaw, OpenCode.
- "Update on read" is literal: every recall that returns a memory writes back `retrieval_count + 1`, `last_retrieved = now` (the decay anchor) and `half_life_days + 2`, unless the memory is net-marked wrong (then only the count moves).
- Strength = `0.5^(days_since_last_retrieval / (half_life * reward_factor)) * (1 + 0.1*log2(retrieval_count+1)) * emotional_multiplier`, clamped to [0,1], times a wrong-mark penalty `0.5^min(net_wrong, 3)`. Retrieval score multiplies relevance by `0.5 + 0.5*strength` and `0.8 + 0.2*recency`.
- The repo's own audits say: outcome feedback (`hippo outcome --bad`) is the mechanism with the clearest win (marked-bad memory in top 5: 71.9% to 0.0% on synthetic E1); supersession helps; age decay showed no measurable effect; sleep consolidation cost recall (-3.6 pp hit@5); the "physics" mode hurts (about -20 pp).
- The cited "R@5 = 74%" is an old v0.11 BM25-only number on LongMemEval `oracle` split with pooled retrieval; the README says it is not comparable to modern per-haystack numbers (98.0% MiniLM hybrid, 99.8% voyage). Opt-in TypeSafe Jev reranker raises R@1 0.41 to 0.62 on a private store but did not beat a free local cross-encoder on answer rate.

## What it claims / describes
Positioning (README): "Hippo learns what is wrong and stops repeating it. Good memory is knowing what to forget: what turned out wrong, what got replaced, what nobody used." The README explicitly downgrades the neuroscience framing: "The design borrows from the hippocampus (decay, three layers, sleep consolidation), but that is inspiration. We have not measured decay or sleep making recall better."

Architecture, step by step:
1. **Layers** (`src/memory.ts`, `enum Layer`): `buffer` (session-only, no decay), `episodic` (default for writes; decays), `semantic` (created by sleep merges; `sem_` id prefix), `trace` (ordered action to outcome sequences, auto-promoted from completed sessions). Separate "working memory" scratchpad: max 20 entries per scope, lowest-importance evicted, cleared between sessions.
2. **Write** (`hippo remember`, `api.remember`, MCP `hippo_remember`, importers, git learner, capture hooks): `createMemory()` builds a row with `strength 1.0`, `retrieval_count 0`, derived half-life, default confidence `verified` for manual writes; optional salience gate; `writeEntry()` persists to SQLite and mirrors; optional async embedding; optional LLM fact extraction.
3. **Read** (`hippo recall`, `hippo context`, MCP `hippo_recall`/`hippo_context`, HTTP): candidate load (SQLite FTS5 then JS scoring), superseded rows filtered out (`api.ts:818: all.filter((e) => !e.superseded_by)`), hybrid BM25 plus cosine scoring times strength, recency, outcome and tag boosts, MMR diversity, optional reranker, token-budget fill, then **write-back strengthening** of the returned ids (`strengthenRetrieved` in `src/store.ts:1786`, called from `cli.ts:2032`, `api.ts:739`, `api.ts:2843`, `mcp/server.ts:716,1165`).
4. **Feedback**: `hippo outcome --good|--bad` applies to the ids of the last recall (`last_retrieval_ids` meta key) or `--id`. Changes both a fast ranking nudge and slow decay rate.
5. **Sleep** (`hippo sleep`, run by the SessionEnd hook, by the daily 6:15am runner, and auto when 50 new memories accumulate `autoSleep.threshold: 50`): learn from git commits, import MEMORY.md, then `consolidate()` phases: 1 decay pass (below 0.05 strength goes dormant or is deleted), 1.4 auto-promote sessions to traces, 1.5 replay (rehearse 5 sampled memories with the same `markRetrieved` write), 1.6 batch LLM extraction, 1.7 to 1.9 DAG summaries (L2 topic, L3 entity profiles), 2 physics simulation (off by default), 3 merge pass (episodic clusters into a semantic memory), 4 log run; plus dedupe and auto-share to the global store.
6. **Invalidation / supersession / conflicts**: `hippo learn --git` detects migration and breaking-change commits and weakens matching memories; `hippo invalidate "<pattern>"`; `hippo decide --supersedes`; `hippo supersede`; conflict detector on overlapping memories with opposite polarity; `hippo reject` writes a content-hash tombstone that blocks the value from being re-written by any path including merges.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| LongMemEval R@5 (the cited 74%) | 74.0% | n/a | v0.11, BM25 only, `longmemeval_oracle`, pooled (non-per-haystack) retrieval, 500 q | README: pooled-oracle numbers "not comparable to per-haystack figures"; not re-verified in audit round 2 (bounded "at most 1.2 pp") |
| LongMemEval oracle v0.11 BM25-only R@1 / R@3 / R@10 / answer-in-content@5 | 50.4 / 66.6 / 82.6 / 46.6% | | same | |
| LongMemEval oracle v0.28 hybrid BM25+cosine R@1 / R@3 / R@5 / R@10 / AiC@5 | 46.6 / 67.0 / 73.8 / 81.0 / 49.6% | v0.11 BM25-only | pooled | hybrid was not better at R@5 than BM25 alone |
| v0.28 R@5 by question type | single-session-assistant 100.0, knowledge-update 89.7, multi-session 72.2, temporal-reasoning 72.9, single-session-user 62.9, single-session-preference 20.0 | | n = 56/78/133/133/70/30 | knowledge-update R@10 96.2 |
| LongMemEval `_s_cleaned` per-haystack, MiniLM-L6 local | dense-only R@5 96.8; best hybrid R@5 98.0; R@1 88.4 | gbrain 97.6 | benchmark scripts index every turn and fuse BM25 with dense ranks, best of 5 settings | "not `hippo recall`, and a default install has no embedder"; 95% CI about +/-1.2 pts, so a tie with gbrain; June build 98.6 |
| same, voyage-3-large (paid) | 99.8 R@5, R@1 94.6 | | measured 2026-06-09, not re-run | |
| Unified 19,195-session store (no per-question haystack) R@5 | MiniLM 47, voyage 56 | | June 2026 | "where we expect the memory lifecycle to matter... It is not shown yet" |
| LoCoMo evidence recall@5 | overall 0.363 (single-hop 0.239, multi-hop 0.491, temporal 0.169, open-domain 0.450, adversarial 0.226) | 2.10x April v0.32.0 baseline | v1.25.0, MiniLM, `hippo recall --budget 4000`, 1,982 q, no LLM judge | n=1 run, predates determinism fix; not comparable to LLM-judge LoCoMo accuracy |
| Jev reranker, private dev store, n=300 q, 40 candidates | R@1 0.6167, R@5 0.7400, MRR 0.6719 | base 0.2600/0.4600/0.3584; cross-encoder 0.4133/0.6133/0.5086 | 2000-draw paired bootstrap, 98.75% intervals; Jev minus CE R@1 +0.2033 [0.1333, 0.2733] | recall at token budget tied (+0.0067); R@1 margin held 20/20 seeds, permutation null 0/200 |
| Jev reranker, LongMemEval n=500 | Jev minus CE R@1 +0.0700 [0.0200, 0.1200]; R@5 +0.0380 [0.0000, 0.0740] tied | | | CE did not beat base on any ranking metric here |
| Jev graded answers, LongMemEval n=150 exact-answer | Jev vs CE at 5 memories -0.0067 tied; Jev top 2 vs base top 40 -0.0133 tied (about 600 vs 12,000 tokens); all arms at 2 memories: base 0.0867, CE 0.1067, Jev 0.1400 | CE vs base at 5: +0.0467 [0.0133, 0.0867] | 98.33% intervals | "An answer win over the free cross-encoder was not shown"; one question set, one answering model |
| Jev cost / latency | p50 295 ms, p90 414 ms, max 953 ms; 0.12 USD / 300 calls (about 0.0004 USD per recall) | | 40 candidates per call | scores vary up to 0.06 run to run; 97 distinct values over 12,000 scores |
| Outcome nudge (audit R2c): marked-bad memory still in top 5 | 0.0% | 71.9% (BM25 static) | synthetic E1, 20 sessions, seeds 101-120, benefit +71.9 [67.8, 75.8] | every mark in E1 is correct; real `--bad` marks the whole recall batch; also +4.9 pp currentR5 |
| Search recency factor (R2a) currentR5 | recency-off better by 6.1 pp [4.9, 7.3] | full@365 | E1 | but recency-off raises stale intrusion 88.2% to 94.2%, cleanStaleR5 -5.1 pp; not changed in 1.46.0 |
| Age decay (R2b) currentR5 | full@365 minus decay-off -0.7 pp [-1.4, 0.1] | | E1 | "NO MEASURABLE EFFECT"; E1 too short for a 365-day half-life to act |
| Sleep consolidation (R-L4) hit@5 | -3.6 pp [-5.8, -1.4] slept vs never-slept | | LongMemEval stores, text-credit scorer | scorer-dependent (+0.4 and +2.2 under others); "No scorer here shows sleep helping recall" |
| Physics mode hit@5 | -21.6 (slept), -19.6 / -19.4 (never-slept) pp vs hybrid | | LongMemEval | physics default off (`src/physics-config.ts`: "MRR 0.68 vs 0.84, R@5 74% vs 84%") |
| Decay default: currentR5 (current fact in top 5) | 75% at 365 d | 29% at 7 d | E1 seeds 21-40; +45.5 [43.9, 47.1] | 730 d and decay-off tied with 365; default moved 7 to 365 in 1.46.0 |
| Decay default: cleanTrapR5 | 54.9% at 365 d | 22.2% at 7 d | trap-exposed queries | raw trap persistence looked better at 7 d only because everything decays |
| Live store dry-run sleep (2,201 memories) | would remove 777 / 1,438 / 1,923 at +30 / +90 / +365 days with stored half-lives; 0 with +358 d added | | author's own store | motivates the half-life migration |
| Memory-value rescue (opt-in) held-out retention | 0.4897 | 0.4203 best hand-set baseline | learned on LongMemEval retention benchmark | usage-feature signs "reflect that benchmark's simulated usage, NOT real usage value" |
| Incident scenarios (E1.3) | 10 of 10 beat transcript replay | transcript replay | staged Slack corpus | |
| Sequential Learning Benchmark | magnitude RETRACTED (v1.7.9) | | 50 tasks, 10 traps | "The mechanism is shipped; no magnitude is currently claimed" |
| Tests | 3,500+ on a real database, no module mocks | | | |

## Mechanism details you could implement

**Data model** (`src/memory.ts: interface MemoryEntry`; SQLite `memories` table in `src/db.ts` v1 plus ALTER migrations): `id`, `created`, `last_retrieved`, `retrieval_count`, `strength` (cached 0..1), `half_life_days`, `layer`, `tags` (`tags_json`), `emotional_valence` (neutral|positive|negative|critical), `schema_fit` (0..1), `source`, `outcome_score`, `outcome_positive`, `outcome_negative`, `conflicts_with`, `pinned`, `confidence` (verified|observed|inferred|stale), `content`, `parents`, `starred`, `trace_outcome`, `source_session_id`, `valid_from`, `superseded_by`, `extracted_from`, `dag_level` (0 leaf, 1 extracted fact, 2 topic summary, 3 entity profile), `dag_parent_id`, DAG cache columns, provenance envelope `kind` (raw|distilled|superseded|archived), `scope`, `owner`, `artifact_ref`, `tenant_id`, `origin_project`. Other tables: `memory_conflicts`, `consolidation_runs`, `audit_log`, `rejected_values` (tenant_id, sha256 digest of normalized content, reason), `dormant_memories` (entry_json, reason, strength, dormant_at), token ledger, FTS5 `memories_fts(id UNINDEXED, content, tags)`. `kind='raw'` rows are append-only via a trigger.

**Half-life at write** (`deriveHalfLife`, `DEFAULT_HALF_LIFE_DAYS = 365`, configurable `defaultHalfLifeDays`):
```ts
if (entry.tags?.includes('error')) hl *= 2;
if (entry.schema_fit > 0.7) hl *= 1.5;
if (entry.schema_fit < 0.3) hl *= 0.5;
```
Decisions, incidents, processes, policies, skills, project briefs, customer notes: 90-day half-life constants. `schema_fit` = IDF-weighted tag overlap with existing store plus content-token overlap (tokens longer than 3 chars); 0.5 when the store is empty. Note: the README "error memories" example still says "14d instead of 7d", which is stale relative to the 365-day default (inference: an error memory now starts at 730 d).

**Strength** (`calculateStrength`, `src/memory.ts`):
```ts
const wrongPenalty = Math.pow(0.5, Math.min(netWrong(entry), MAX_WRONG_HALVINGS)); // MAX 3
if (entry.pinned) return wrongPenalty;
let effectiveHalfLife = entry.half_life_days * rewardFactor;
const decay = Math.pow(0.5, daysSince / effectiveHalfLife);   // daysSince from last_retrieved
const retrievalBoost = netWrong(entry) > 0 ? 1.0 : 1 + 0.1 * Math.log2(entry.retrieval_count + 1);
const raw = decay * retrievalBoost * emotionalMultiplier;  // clamp [0,1] then * wrongPenalty
```
- `rewardFactor = 1 + 0.5 * (pos - neg) / (pos + neg + 1)` (1.0 with no feedback). 5 good, 0 bad gives about 1.42; 0 good, 3 bad gives about 0.63.
- `netWrong = max(0, outcome_negative - outcome_positive)`.
- Emotional multipliers: neutral 1.0, positive 1.0, negative 2.0 (scaled by env `HIPPO_LOSS_AVERSION_RATIO`, default 1.0, minimum 0.5), critical 2.0.
- Decay basis config `decayBasis`: `clock`, `session` (days divided by avg session interval), or `adaptive` (default; effective half-life multiplied by avg session interval when that interval is over 1 day).

**Update on read** (`markRetrieved`, `src/search.ts:1257`, persisted by `strengthenRetrieved`, which updates only four columns inside `BEGIN IMMEDIATE`, best effort, never fails the read):
```ts
if (e.superseded_by) return e;
const wrong = netWrong(e) > 0;
retrieval_count: e.retrieval_count + 1,
last_retrieved: wrong ? e.last_retrieved : now.toISOString(),
// +2 days half-life per retrieval (PLAN.md); a wrong memory keeps both, since last_retrieved is the decay anchor
half_life_days: wrong ? e.half_life_days : e.half_life_days + 2,
```
So one read does three things: resets the decay clock (largest effect), adds 2 days of half-life (additive, unbounded), and bumps the log retrieval boost (retrieval_count 1 gives x1.1, 3 gives x1.2, 7 gives x1.3). Confidence is deliberately not changed on read ("it is an epistemic tier, not a recency signal"); the derived "aged" flag (not pinned, not verified, last_retrieved over 30 days ago) disappears because last_retrieved is reset. What gets strengthened is whatever survived budget filtering and was returned, after any reranker. The ablation env `HIPPO_ABLATE_RECALL_BOOST` disables all three effects.

**Replay (update without a user read)** (`src/replay.ts`, consolidate phase 1.5): each sleep samples `replay.count` (default 5) survivors weighted by `rewardSignal = max(0.1, 1 + pos*0.5 + (pos-neg)*0.25)`, valence weight (neutral 1.0, positive 1.3, negative 1.5, critical 2.0), `underRehearsed = 1/(1+retrieval_count)`, `idleBoost = 1 + log1p(idle_hours)*0.1`, then runs `markRetrieved` on them.

**Retrieval score** (`hybridSearch`, `src/search.ts`):
- BM25: k1 = 1.5, b = 0.75, `idf = ln((N - df + 0.5)/(df + 0.5) + 1)`; tokenizer lowercases, strips non-word chars, drops 1-char tokens. Normalized by max BM25 in the candidate set.
- `base = bm25Weight * normBm25 + embeddingWeight * cosine`, `embeddingWeight` default 0.6 (`embeddings.hybridWeight`), or RRF fusion (`scoring: 'rrf'`) over BM25, cosine and optional graph ranks. Without embeddings it is BM25 only.
- `composite = base * (0.5 + 0.5*strength) * (0.8 + 0.2*recency)`, `recency = exp(-age_days_since_created / 30)`.
- Multipliers: decision tag 1.2; path-tag match up to 1.3; outcome nudge `clamp(1 + 0.15*tanh((pos-neg)/2), 0.85, 1.15)`; active scope match 1.5, mismatch 0.5; `extracted` tag 1.3; temporal cue words ("latest", "first", etc.) 0.8 to 1.2 by position in the time range; DAG summary deboost 0.85 (`HIPPO_SUMMARY_DEBOOST`) with a 1.05 boost if rebuilt in the last 7 days; `search.localBump` 1.2 for local over global store.
- MMR on by default when embeddings are loaded, lambda 0.7, window capped at 100 candidates. Optional reranker on top-K (default 50; 40 for Jev). Token budget: default 4000 for recall, 1500 in hook context; tokens estimated as chars / 4.
- Embeddings: optional, `enabled: 'auto'`, default model `Xenova/all-MiniLM-L6-v2` via locally installed Transformers.js, or opt-in OpenAI / Voyage / Cohere API embedders. Nothing auto-installed.

**TypeSafe Jev reranker** (`src/rerankers/jev.ts`, registry in `src/rerankers/index.ts`, opt-in `hippo recall "<q>" --reranker jev`, `--reranker-top-k` overrides):
- Endpoint `https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer $TYPESAFE_API_KEY`, one POST per recall.
- Body: `{ state, model, questions }`. `state` = `"Query: <q>\n\nNumbered candidate memories from an AI coding agent's project store:\n\n[1] <content>\n\n[2] ..."`, each candidate cut to 1,200 chars and passed through `redactSecrets`. `model` = `HIPPO_JEV_MODEL` or pinned `jev-1.13.0` ("Pinned, not `jev-latest`"). `questions` = `{ c1: { type: 'noul', instructions: 'Probability that candidate 1 (numbered in the state above) helps answer the query.' }, c2: ... }`.
- Response parsed from `answers.cN.noul`, must be a finite number in [0,1] for every candidate, else the whole response is voided ("A half-scored list ranks worse than the order it would replace").
- Timeout `HIPPO_JEV_TIMEOUT_MS` default 5,000 ms. Any failure (key unset, non-2xx, timeout, bad answers) warns once per process and falls back to the local cross-encoder `Xenova/ms-marco-MiniLM-L-6-v2`; if that is missing too, input order is returned. Stable sort, ties keep prior relevance order.
- Jev is used only for ranking. It is not used as a write gate, extractor or abstention signal anywhere in the repo (searched `src/` for jev/typesafe: only `cli.ts` and `src/rerankers/`). Other rerankers: `cross-encoder`, `llm`.

**Write-side gates**:
- Content minimum 3 chars (`createMemory` throws).
- Salience gate (`src/salience.ts`, **off by default**, `salience.enabled`): Jaccard overlap (`textOverlap`) against the last 20 memories; overlap above 0.6 means `skip` as duplicate, unless it is an error: then `store` (score 0.7), or `start_weak` (strength 0.3, half-life halved) if 4 or more recent error memories. Novel error score 0.9; novel non-error 0.5, +0.15 structured tags, +0.1 over 100 chars, +0.1 over 300 chars.
- Rejected-value tombstones block re-insertion by any path including sleep merges.
- Secret detector: a faded memory flagged as a secret is deleted, never kept dormant; Jev input is redacted.
- LLM fact extraction: `extraction.enabled: 'auto'`, model `claude-sonnet-4-6`, needs `ANTHROPIC_API_KEY`; best effort.

**Forgetting**:
- Decay threshold `DECAY_THRESHOLD = 0.05` at sleep. Below it, a retirable memory (not pinned, not `raw`, not backing a first-class object) goes to `dormant_memories` (default `dormant.enabled: true`), leaving recall entirely; restore gives a fresh recall clock; dormant rows expire after `dormant.retentionDays` 180.
- Optional learned "memory-value rescue" (`memoryValue.enabled`, default false): keeps a condemned memory if it is in the top 30% of its tenant by a learned linear score; can only rescue, never delete; inactive under 10 non-pinned memories.
- Invalidation (`src/invalidation.ts`): token match of 0.5 or more, or tag match, gives `half_life_days = max(1, floor(hl / 2))` and `confidence = 'stale'`. Supersede via `decide --supersedes` halves half-life and marks stale; superseded rows are excluded from recall by default (`--include-superseded`, `--as-of` flags exist).
- Conflict resolution `hippo resolve <id> --keep <mem>` weakens (or `--forget` deletes) the loser.

**Consolidation merge** (`src/consolidate.ts`): episodic, not superseded, not `extracted`; per tenant; greedy cluster around each seed by Jaccard overlap of 0.35 or more (`MERGE_OVERLAP_THRESHOLD`), `MERGE_MIN_CLUSTER = 2` (README says "Three or more related episodes get merged"; the code constant is 2). Creates a semantic memory with union of tags, strongest valence, `schema_fit 0.7`, `confidence 'inferred'`, `source 'consolidation'`; sources get `half_life_days = max(1, floor(hl * 0.3))` so they fade. Conflicts: polarity detected on first 40 words, then stopword-filtered Jaccard of 0.5 or more with at least 2 rare shared tokens.

**MCP tools (13):** `hippo_recall`, `hippo_assemble`, `hippo_drill`, `hippo_remember`, `hippo_outcome`, `hippo_context`, `hippo_status`, `hippo_learn`, `hippo_conflicts`, `hippo_resolve`, `hippo_share`, `hippo_peers`, `hippo_predict_baserate`.

**Claude Code hook wiring**: SessionStart (`hippo context --auto --budget 1500`), UserPromptSubmit (`hippo context --pinned-only --include-recent 5 --format additional-context`, skipped when unchanged, resent every 10 skips `pinnedInject.refreshTurns`), PreCompact (snapshot plus extraction), PostCompact, SessionEnd (`hippo sleep`), PostToolUseFailure (`hippo capture-error`). Context framing default `observe` ("Previously observed (date): ..."), also `suggest`, `assert`.

**Other config keys** (`src/config.ts` DEFAULT_CONFIG): `defaultBudget 4000`, `defaultContextBudget 3000`, `autoLearnOnSleep true`, `autoShareOnSleep true`, `global.enabled true`, `mmr {enabled true, lambda 0.7}`, `physics.enabled false`, `multihop.enabled false`, `ambient.enabled true`, `contextProjectIsolation true`, `autoTraceCapture true`, `autoTraceWindowDays 7`, `gitLearnPatterns` [fix, revert, bug, error, hotfix, bugfix, refactor, perf, chore, breaking, deprecate]. Eval-only ablation env flags: `HIPPO_ABLATE_RECALL_BOOST` and others in `src/ablation.ts`; `HIPPO_FAKE_NOW` for simulated time.

## Limitations, caveats, counter-evidence
- The cited headline (74% R@5 BM25-only) is an early pooled-oracle figure. The repo's own later per-haystack numbers are much higher but come from benchmark scripts, not the product's `hippo recall` path, and "a default install has no embedder".
- LongMemEval is static: "decay and strengthening never act there" (audit caution flags). So none of the LongMemEval numbers test the update-on-read mechanism.
- Author's own audit: age decay no measurable effect on E1 (but E1 too short to test it); sleep consolidation hurts recall by the declared scorer; physics hurts; the search recency factor hurts the current fact on E1. Outcome marks and supersession are "what measured helpful".
- E1 is synthetic, 20 sessions, and every outcome mark is correct; "real bad marks are noisier, since `--bad` marks the whole recall batch".
- "The author built, ran and judged this." Several results are awaiting re-runs (real-data decay replay scheduled 2026-10-24; R4 lane had no verdict after a gate failure).
- Jev reranker: never abstains, no confidence field (0 of 500 calls returned one), scores not bit-stable, coarse (97 distinct values), sends query and memory text to a third party; no answer-quality win over the free cross-encoder shown.
- Half-life additive +2 d per read has no cap in `markRetrieved` (inference: a heavily read memory's half-life grows without bound; at a 365-day base this is small per read but monotone).
- Sequential-learning benchmark magnitude retracted.
- README and code disagree on merge cluster minimum (3 vs `MERGE_MIN_CLUSTER = 2`) and the error half-life example (14 d vs derived 2 x 365 d).

**On the trend's watch question (feedback loops that reinforce frequently recalled wrong memories):**
- There is an explicit guard, but it only fires after a negative mark. If `outcome_negative > outcome_positive`, `markRetrieved` stops resetting `last_retrieved` and stops adding half-life, `calculateStrength` drops the log retrieval boost, and strength is halved per net wrong mark (up to 3 halvings, x0.125). The fast ranking nudge adds up to x0.85. Replay's reward signal floors negative-dominated memories at 0.1 weight. Rejection tombstones and supersession remove wrong values outright.
- Without a mark, there is no guard: a wrong but frequently recalled memory gets its clock reset and half-life extended on every read, and replay rehearses under-rehearsed memories regardless of correctness. So the loop is broken by outcome feedback, not by the read mechanism itself (inference).
- Batch marking (`--bad` on the whole last recall) means correct memories that were recalled next to a wrong one also get penalized, and a later `--good` on a batch can cancel a memory's net-wrong status (inference from the formulas).
- The measured evidence on this is the E1 R2c lane: outcome nudge took marked-bad top-5 persistence from 71.9% to 0.0%, under perfect marks. No measurement of unmarked wrong-memory reinforcement exists in the repo (not stated).

## Takeaways for tuning a memory stack
- Treat read-time strengthening as three separate knobs: decay-clock reset on read, additive half-life growth, and a log-count boost. Hippo's constants (+2 d, 0.1*log2) are small; the clock reset dominates.
- Gate reinforcement on correctness: copy the `netWrong > 0` rule (a net-wrong memory does not get strengthened by reads) and the capped multiplicative wrong penalty `0.5^min(n,3)`.
- Put strength and recency in bounded multipliers (`0.5 + 0.5*s`, `0.8 + 0.2*r`) so a weak but exactly relevant memory can still rank.
- Invest in explicit feedback and supersession before decay or sleep merges: in this repo those are the only mechanisms with measured wins; age decay was a null and consolidation merge cost recall.
- If you use long half-lives (365 d), decay rarely matters within weeks; a 7-day half-life lost the current fact far more often (29% vs 75% currentR5).
- Keep faded memories dormant (restorable, out of recall) rather than deleting; log restores as a "forgot it, then needed it" signal for tuning.
- For a Jev-style reranker: pin the model version, batch all candidates in one call, void partial answers, fall back to a local cross-encoder, and do not threshold on its scores for abstention. Its measurable benefit is a shorter context (2 memories performing like 5), not better answers.
- Benchmark update-on-read on a dynamic workload (repeated sessions with fact changes), because static retrieval benchmarks like LongMemEval never exercise it.

## Open questions
- Does unmarked reinforcement of wrong memories happen in practice, and how often? No measurement in the repo.
- Real-data decay replay result (scheduled 2026-10-24) and whether a half-life grid is ever triggered.
- Would a per-memory outcome API (instead of batch `--bad`) change the R2c effect size under noisy real marks?
- Which sleep phase causes the -3.6 pp recall cost (merge is the "first suspect")?
- Does the recency factor get turned off after the round-3 stale-fact check?
- Would Jev (or any decision model) help more as a write gate or abstention signal than as a reranker here? Not tested in this repo.

---
