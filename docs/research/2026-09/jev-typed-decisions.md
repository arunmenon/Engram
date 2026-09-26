# Jev (TypeSafe System One) as a typed-decision layer in Engram

**Date:** 2026-09-25
**Inputs:** the independent field guide *How to Use Jev with LLMs* (Sep 2026); TypeSafe's public docs and launch blog; the [judgment-point catalogue](judgment-points-catalogue.md).
**Verification note:** `typesafe.ai`, `docs.typesafe.ai` and `evals.typesafe.ai` are blocked from this environment. Vendor facts below were read from verbatim Markdown mirrors of the docs (fetched 2026-09-23) and from TypeSafe's own GitHub repositories (`typesafe-sdk-python`, `typesafe-sdk-js`, `skills`, `system-one-adapter-python`). Each is labelled **vendor states** or **third-party**. Re-check against the live docs before relying on limits or prices; the Models page says limits "can change without notice".

## 1. What Jev is, in one paragraph

**Vendor states:** Jev is "the first System One model": send a *state* (string, JSON object, or array; text only) plus a map of typed *questions*; get typed answers with probabilities. Three primitives: **Choice** (pick one of up to 255 options; returns the option, a probability per option, and a `confidence`), **Score** (position on an ordered rubric of 2–10 levels; returns a probability-weighted score, per-level probabilities, `confidence`), **Noul** (probability that a statement is true; no separate confidence). All questions in a request are evaluated independently and in parallel against the same state; adding questions "barely changes the response time". Context budget: 64k tokens per request, 32k for state + longest question. It does not generate text, code, or explanations. Pricing: $0.042 per million input tokens, output free. Rate limit published as 250k tokens/s and 1,200 requests/min, "adjusting dynamically". Hosted in the US only; no VPC/on-prem/weights; zero-data-retention is enterprise-only. Python (`typesafe-sdk`, ≥3.10) and JS SDKs; OpenRouter and Vercel AI Gateway routes.

**Latency:** vendor gives "70–500 ms end-to-end" and "around 100 ms"; no percentiles. **Third-party** wall-clock p50s range 130–600 ms depending on region and gateway.

**Accuracy/calibration:** vendor's own workflow evals put Jev at 67.8 % mean agreement with a GPT-6/Fable-5.1 reference (vs 74.1 % for the best LLM) at ~$0.0004 and 0.4 s per case. **Third-party** audits: ECE 0.02–0.03 on standard classification sets, but 0.1–0.3 on out-of-distribution or policy-dependent labels; removing an "abstain" option from a Choice pushed ECE from 0.02 to 0.79; paired Nouls do not sum to 1; run-to-run variance exists (not deterministic). The vendor's "can't hallucinate" claim means *schema conformance*, not truth — its own skill file says "Typed output guarantees the interface, not truth."

**Known weaknesses (vendor's jaggedness page):** literal reading; math, counting, numeric formats; date comparison ("reads dates as text"); double negatives; large irrelevant state degrades accuracy; can be steered by injected instructions in the state; no invariants across separate questions.

## 2. Where the field guide is right for Engram

The guide's core rule — *LLM generates, Jev makes bounded semantic decisions, deterministic code keeps authority, and every decision leaves a receipt* — matches two independent findings from the code review:

- Engram's hot path already has **no LLM** on it by design, but its *async* path asks one LLM call to propose entities, preferences and skills **and** grade its own confidence and source type (E2/E6). That is the "self-approval" anti-pattern the guide names.
- Almost no decision in Engram is recorded with its inputs (catalogue cross-cut (d)). The guide's "decision receipt" is the same primitive that the [RSI positioning](rsi-positioning.md) needs for outcome feedback and that the provenance literature (Eywa, MemIR, MemTX) treats as mandatory.

So the value of Jev to Engram is less "cheaper LLM calls" and more "a place to put the judgments that currently have no judge, in a form that can be logged, replayed and calibrated".

## 3. Plug-in map

Ordered by (impact × ease). Ids refer to the catalogue.

### Tier A — do first (async path, no latency risk, fixes a known defect)

| # | Judgment point | Today | With Jev | Why here |
|---|---|---|---|---|
| A1 | **Extraction acceptance gate** (E2, E5, E6) | LLM self-reports confidence and source type; grounding is a word-overlap heuristic | After the extraction LLM returns items, one Jev call per session with a battery over `{transcript_excerpt, item, quote}`: Noul `quote_supports_item`, Choice `source_type ∈ {explicit_stated, implicit_behavioural, inferred, unsupported}`, Score `strength`. Code applies ceilings from the *Jev* source type, not the LLM's. Items below threshold go to a `tentative` state rather than being dropped (see RSI doc) Build it as one cheap battery with escalation to a larger battery only when borderline (top score in [0.3, 0.7] or low confidence), and measure the escalation tier on the held-out split: in jevmem the larger tier scored *below* the cheap one (90.9 % vs 95.5 %, digest D8 addendum) | Removes the self-approval conflict; independent grounding check; vendor's citation-check and RAG-passage cookbooks are the same shape. Extraction is already async, so +0.3 s is invisible |
| A2 | **Entity-match arbitration** (E9–E12) | Tier 2b = MiniLM on the *name only*, top-1, 0.90/0.75 thresholds, types not compared; closure erases evidence | Deterministic recall (exact/alias/fuzzy/embedding top-k) → one Jev call over the candidate set: Score `same_entity ∈ {different, related, same}` per candidate plus Nouls on the disagreeing fields (same type? same owner/org?). Store the score and the field-level answers on the `SAME_AS`/`RELATED_TO` edge. Closure keeps the original evidence | The vendor's own entity-alignment cookbook is exactly this (3-level Score + companion Nouls, 450 pairs). Replaces the LLM tier the ADRs promised but the core never implemented |
| A3 | **Delete / archive gate** (C8, C9, C10, C11) | Age + importance + access-count thresholds; no archive; wrong decisions irreversible | Before any DETACH DELETE: batch candidates, ask Noul `still_referenced_by_active_summary_or_goal`, Noul `contains_constraint_or_decision`, Score `evidential_value`. Code: high → keep; medium → archive-then-delete; low → delete. Receipt stored as a `system.forgetting` event | Makes forgetting auditable and gives the RSI loop a place to learn thresholds per tenant. Governance-Decay and AuthMem-Bench results say summaries silently drop constraints — this is the guard |
| A4 | **Duplicate-with-conflicting-payload** (I2) | Same `event_id` → old position returned; content never compared | Code compares a content hash first (deterministic). Only when hashes differ: Noul `payloads_semantically_equivalent` → equal: accept as replay; different: reject with 409 per ADR-0026's conflict rule | Cheap, closes a gap-analysis finding, and the deterministic hash handles >99 % of cases without a model call |
| A5 | **Preference / belief supersession** (E15, E16, B1) | Free-text key match + "most recent wins"; no SUPERSEDES edge; belief logic dead | Pairwise over candidates sharing an entity/category: Choice `relation ∈ {same, supersedes, contradicts, unrelated}` + Noul `newer_is_more_reliable_given_sources`. Write a typed edge with the distribution as justification. **Supersede only on two signals**: `contradiction ≥ 0.7` *and* a named target id; the old node stays with a `superseded` state and is excluded from default recall, never deleted (jevmem: 25/27 reversals, 0 wrong targets, 0/16 false supersedes) | This is the CONTRADICTS/SUPERSEDES machinery ADR-0009 promised. Nous/TEPA/MemTX all want an explicit, recorded update decision |
| A6 | **Staleness audit** (new; today nothing revisits a Belief/Preference/Decision once written) | Decay lowers scores by age; content is never re-checked | Consumer 4 job: for each live Decision/Belief, batched ~60 per call, Noul `still_true_given_snapshot` over `{item, recorded_at, snapshot}` where the snapshot is the current state of what the item is about (for PDLC: repo tree, manifest, README head; for support: the entity's current attributes). Below the fitted threshold (jevmem uses 0.4) set `stale_flag`; a later pass may clear it. **Never delete on this signal** | The T5 rule set made concrete; the cheapest defence against serving a stale Decision as current. Zero hot-path cost |

### Tier B — retrieval-side, shadow-mode first

| # | Judgment point | Today | With Jev | Caution |
|---|---|---|---|---|
| B0 | **Retrieve-or-not gate in the harness adapters** (new; not in the catalogue) | SDK/plugins always call `/v1/context` or `/subgraph` | In the harness hook (e.g. Claude Code `UserPromptSubmit`, LangChain callback), one call per prompt: Noul `memory_would_help`, Choice `intent`, Score `context_budget`. Honours "without using memory…". Only then call Engram with the chosen intent/budget | Cheapest and most user-visible Jev use; supermemory reports it works well in exactly this hook (digest D4). Lives in ADR-0015 adapters, not in the core |
| B1 | **Neighbour / proactive-context admission** (R6, R8) | Every fetched neighbour is returned and labelled "proactive" with no relevance test | After graph expansion, **one listwise Choice over the candidate pool** (`{query, intent, candidates[]}` → ranked selection), **always returning at least one**, **never offering a "none relevant" option**; record the distribution in `meta` | Revised per digest D8: Hindsight measured listwise Choice at recall@1 0.94 vs 0.87 for a per-candidate Noul, with 30× fewer calls; a "none of these" option emptied 35/200 queries and a "nothing" level cut gold retention 0.81 → 0.65; pruning lifted precision but dropped 19 % of gold. Scores are rank positions within a call — never port an absolute floor. Adds ~0.2–0.5 s to `/subgraph`; run behind a flag and measure the counterfactual |
| B4 | **Stop rule for expansion** (new; today only `max_nodes` bounds retrieval) | Fixed caps | Per expansion round, one call with Nouls `evidence_sufficient`, `missing_evidence`, `contradiction`, `continue_useful` over `{query, selected_evidence, depth}`; stop at ≥0.95 / <0.15 / <0.15, or `continue_useful` <0.15; hard caps stay in code | Jev-Mem's design (digest D8), the most complete control loop in the evidence but **unablated** — fit thresholds on Engram's own held-out set before trusting them |
| B2 | **Intent classification** (R1, R2) | Keyword regex; optional LLM classifier | Choice over the 8 intents (+ `unclear`) with distribution; the distribution *is* Engram's multi-intent weight vector | Natural fit and cheap, but the keyword classifier is not the bottleneck today; the eval harness never even exercises it. Do B1 first |
| B3 | **Importance at ingest** (I4, C5) | hint or constant 5; later overwritten by centrality | Score `salience` over `{event_type, tool, payload_excerpt}` at enrichment time; keep hint as a prior | Async, cheap. Gives the decay model a real importance signal instead of a constant |
| B5 | **Injection gate on served memory** (new) | Extracted items, taken from untrusted transcripts, are returned by `/v1/context` and re-injected into agent prompts unchecked | At enrichment time (async), Noul `contains_instructions_aimed_at_an_automated_system` over each extracted item; items ≥ threshold (jevmem: 0.5) get `verified=false` and are withheld from serving or served under a "facts, not instructions" frame. Verified state is keyed by a hash of the item text so re-extraction re-checks | jevmem blocked 20/22 planted lines with 0/22 false blocks (44 lines, author-written). Tell the Noul that a changed project rule is not an injection, or reversals get blocked. Shadow first; measure false blocks on real tenant data |

### Tier C — do not do

- **Summarisation, HyDE, extraction itself** (C3, R18, E2): generation; Jev cannot do it.
- **Anything numeric or temporal**: recency, decay, tier assignment, episode boundaries — the jaggedness page says Jev reads dates as text. Keep these in code.
- **Ranking by probability across items**: gate, don't sort.
- **Replacing the event-envelope validator** (I1): exact rules belong in Pydantic.

## 3a. Field evidence from other memory systems (Sep 2026)

Two practitioner reports arrived after the map above was drafted; both confirm its shape and sharpen two rules.

- **supermemory** (digest D4) benchmarked Jev on BEIR reranking: a **Noul used as a delete gate "kept nothing"**, while Noul-as-sort and a 10-level Score both worked (Score best). Rule: *for graded decisions use Score with an anchored rubric; reserve Noul for genuinely binary claims and calibrate its threshold per question* (A3 above should be a Score on `evidential_value`, not a Noul). Their sentence-level pre-extraction filter saved 58 % of tokens but broke contextuality — rule: *judge at the granularity where the state carries the context* (turn/episode, not sentence). Their harness-hook "should memory be used for this prompt" worked well → B0.
- **Beacon** (digest D3) gates traces with three Nouls (`task_success`, `reusable_correction`, `evidence_supported`) then promote/review/discard. Two failures: asking Jev for a `reason` returned the literal string `"noul"` (a decision model cannot explain — the LLM or the trace must supply lesson text); and re-running evaluations overwrote reviewed candidate states. Both are already rules here: Tier C, and "keep the receipt on the ledger".

- **jevmem, mika_systems, agentrun** (digest D8 addendum). jevmem is the first end-to-end worked save gate on Jev: two tiers with escalation only when borderline, policy in code, two-signal supersession, per-line provenance hash, an injection gate before serving, and a separate "still true?" audit; its own held-out numbers show the larger battery losing to the smaller one, so *the escalation tier is a hypothesis, not a safety net*. The StarCraft II report (planner + Jev 9/10, Jev alone 0/10) is the clearest evidence that a decision model belongs inside a plan choosing from a closed, freshly rebuilt menu — which is what B4 is and what Tier C forbids. mika's operating rules transfer directly: thresholds by cost of error, shadow per route, batch every question that shares a state (13 questions in one call: 10× faster, 12.2× cheaper), rebuild the option list after every state change. agentrun's `≥ 0.8` is a documented example, not a policy; no threshold in this document is to be copied from another system either — each is fitted on Engram's labelled set (§5, step 1).

## 4. Integration shape

```
domain/decisions.py        # question batteries as versioned constants (battery id, version, question ids, criteria)
ports/decision.py          # Protocol: decide(state, battery) -> DecisionResult; no vendor types in domain/
adapters/typesafe/client.py# TypeSafe SDK adapter; pinned model id; retry policy; timeout; breaker
adapters/typesafe/receipt.py# builds a `system.decision` event: state digest, battery version, model id,
                           # distributions, thresholds, chosen route, latency; appended to the ledger
```

Rules (from the guide, adopted verbatim):
- Deterministic checks first; Jev only among allowed options; a favourable answer is evidence, not authority.
- Every Choice gets a no-match option (`other` / `unsupported` / `unclear`). Third-party calibration collapses without it.
- One shared state, all independent questions in one call. Never one call per candidate when a batch will do.
- Pin the model id while thresholds are calibrated; replay labelled cases on upgrade.
- Fail closed: a missing/failed decision is `review`, never `approve`. (Engram's current pattern of "empty result = success" is the opposite of this.)
- Thresholds per question, per action, per risk class, in `settings.py` — not one global number.
- Keep the receipt on the ledger. It is the provenance for the derived graph mutation and the training signal for the RSI loop.

## 5. Rollout

1. **Offline replay.** Build a labelled set from existing sessions: ~30 cases each for A1, A2, A3 (obvious / ambiguous / no-fit). Run in the Playground first, then via SDK; record distributions.
2. **Shadow.** Run A1–A3 alongside current logic, write receipts, change nothing. Compare to current decisions and to human labels.
3. **Assist.** Surface Jev's answer in admin prune previews and in extraction logs.
4. **Limited automation.** Enable A1 (acceptance ceilings) and A4 (conflict rejection) — low blast radius. Then A2, then A3 with archive-before-delete enforced by code. A6 (staleness flag) and B5 (injection gate, shadow) can join this step because neither deletes or blocks anything until a human turns the flag into policy. Refit thresholds only once ≥ 40 labels exist per battery (jevmem's floor); log raw probabilities, not verdicts; on timeout fall back to the rule path and queue the decision, never retry on the hot path.
5. **Retrieval-side (B1)** only after a fixed eval harness exists (see [landscape](memory-research-landscape.md) §3), because today's harness cannot see the effect.

## 6. Risks specific to Engram

- **Data egress.** State sent to Jev includes transcript excerpts. US-hosted, no ZDR on standard plans, retention "as long as reasonably necessary". This must pass ADR-0016/ADR-0029 tenant policy *before* any semantic call (the guide's "deterministic organisation policy first" rule). Some tenants will have to opt out; the design must degrade to the current rule path.
- **Prompt injection via state.** Transcripts are untrusted; the vendor says Jev can be steered by injected instructions. Keep questions and criteria out of the state; treat "ignore the policy" text as evidence to classify.
- **Vendor concentration.** Single hosted provider, early-access terms ("may not be suitable for production use", no publishing benchmarks). The port interface above keeps the domain free of vendor types; the fallback for every battery is the existing rule.
- **Calibration drift.** Aliases (`jev-latest`) move without notice. Pin; recalibrate on change; keep the labelled set in the repo.

## 7. Bottom line

Jev's best use in Engram is not on the hot read path. It is as the **independent judge for async memory mutations** — extraction acceptance, entity merges, supersession, and deletion — where Engram currently either has no judge or lets the proposer grade itself, and where a typed, recorded decision doubles as the provenance record and the feedback signal the RSI loop needs. Retrieval-side admission (B1) is the second step once evaluation can measure it.
