---
schema_version: 1
artifact_id: N-20260929-30
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104675152235528690", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:adecubed/adebench
claim_cluster: github:adecubed/adebench
feeds: ["memory"]
primary_source: https://github.com/adecubed/adebench
source_commit: 5a2b2db10958b5a79ee6b802957f87e9912a93a6
strength: repo-pinned
pillar_primary: R6
pillar_secondary: ["R2", "R8", "R3"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["deterministic-keyword-checks", "forbidden-retired-values", "id-less-update-probe", "write-back-poisoning-probe", "door-budget-margin", "pressure-from-census", "skip-leaves-denominator", "setup-fingerprint-deltas"], "workload": ["personal-assistant-memory", "engineering-facts-ports-versions", "file-search-top5", "longmemeval-s"], "lifecycle_stage": ["benchmark", "early-version"], "cross_cutting": ["stale-values", "abstention", "judge-sensitivity", "coverage-reporting", "self-poisoning"]}
evidence_grade: {"directness": "high: primary repo README and committed per-system reports read at a pinned commit", "control": "medium: same golden set, harness and weights for every system, but coverage differs (55 to 100 points measured), extraction models and deployment defaults differ per system", "independence": "low: harness written around the maintainer's own ADE Brain, which scores 93.8; all external systems were run by the same maintainer, not by their vendors", "reproducibility": "medium: MIT, no dependencies, synthetic set with a CI-pinned 90.0 reference; external runs need live services and LLM extractors (Hindsight ran gemini-3.5-flash-lite, not the documented model)", "applicability": "medium: facts are engineering-flavoured (ports, versions, repo file search) and the stale checks map to supersession, but only 8 door questions and 4 abstention questions, personal-assistant framing, no long structured artifacts or trace links"}
beliefs_affected: {"supports": ["B3", "B11"], "contradicts": [], "would_create": ["R8/R2: memories that store exchanges and rank by recency can re-serve their own degraded 'no record of that' answers ahead of the true fact (gbrain 2 of 2, Aionforge 2 of 2 poisoned; Hindsight 0 of 2, ADE Brain 0 of 2)", "R6: the judge model can reorder readers on LongMemEval-S (gpt-6-astra 89 vs gemini 83 under GPT-4o, 85 vs 85 under GPT-5.1, same 100 answers)"]}
claim_correction: Post calls adebench a benchmark for agent memory; the README scopes it to personal AI assistant memory, built around the maintainer's own ADE Brain; stale-write coverage is one forbidden-value door question, a 3-check id-less update probe and an opt-in, report-only write-back probe
---

# adebench: a deterministic benchmark for personal AI memory, with stale-value, update and write-back probes (results for Hindsight, gbrain, Dakera, Memoose, Aionforge, ADE Brain)

- **URL:** https://github.com/adecubed/adebench
- **Type:** repo (benchmark harness plus committed reference reports)
- **Author / org:** Adecubed (LICENSE "Copyright (c) 2026 Adecubed"); MIT; package `adebench` version 0.2.15 (pyproject.toml)
- **Date:** commit `5a2b2db10958b5a79ee6b802957f87e9912a93a6`, 2026-09-28 17:59:23 +0200, "0.2.15: Hindsight, the Brain on the synthetic set, and the leaderboard site"
- **Retrieved:** 2026-09-29 (local copy: repos/adebench, shallow clone). Read: README.md, examples/longmemeval/README.md, examples/hindsight_report/reference.md, examples/synthetic_data/cases/{questions,abstention}.json, adebench/mitosis.py and adebench/tokenmizer.py docstrings, pyproject.toml, LICENSE. No repo code was executed.
- **Cited by evidence:** X post 2104675152235528690 by @0xdudoshi ("I maintain adebench, an open benchmark for agent memory. Would be curious to run Nemp on it, especially on stale writes."). Post not re-fetched (x.com returned HTTP 402); text from triage brief. The link between the handle @0xdudoshi and the GitHub owner adecubed is not verified.
- **Relevance to a memory stack:** medium-high for scoping our PDLC memory benchmark (N-SCOPE-20260928-01): it already implements the checks we want for supersession (retired value must not reach the model), abstention, age delivery and write-back self-poisoning, deterministically and without an LLM judge, against the text the agent actually receives.

## TL;DR
- adebench scores 0 to 100 over eight weighted sections (door 25, cards 15, updates 10, time 10, live_state 10, abstention 10, file_search 10, graph 10) on the text that reaches the client through a chosen "door", with deterministic whole-token keyword checks, four states (PASS / FAIL / ERROR / SKIP), SKIP removing weight from the denominator and coverage always reported.
- Stale handling is three separate probes: `forbidden` retired values on a door question (a text containing old and new fails with `STALE`, "a **ban on presence**, not a detection of contradiction"), an id-less `write_fact` update probe (8000 -> 9000, old must never be served, unrelated fact survives, restating adds no copy), and opt-in `--write-back` (a degraded "I have no record of that" answer written through the memory's own write path must not come back through the door).
- Results on the synthetic set (8 door questions, 4 abstention questions): Dakera 96.9 / 100, ADE Brain 93.8 / 100, synthetic reference 90.0 / 100, gbrain 75.4 of 90, Memoose 68.3 of 90, Aionforge 51.8 of 65, Hindsight 36.2 of 55. Denominators differ, so totals are not directly comparable; the README gives pairwise comparisons on shared points.
- Only Dakera (write-time `Supersedes` edge, ">=0.92 cosine") and the ADE Brain pass the update probe fully; gbrain, Aionforge and Hindsight serve both old and new values. No results or adapters for Mem0, Zep, Letta or supermemory; Nemp is not mentioned in the repo. Adapters exist for Mitosis Cortex and TokenMizer without committed results.
- Claim correction: "agent memory" is narrowed to personal assistant memory; stale-write coverage is small (one forbidden-value question, 3-check update probe, 2-question write-back probe by default).

## What it claims / describes
**Target.** "measures the memory of a personal AI assistant the way that memory is actually used", born for the ADE Brain (memory of the Sofia voice assistant), talking to other systems through an adapter (`adebench/adapter.py`; `adebench/ade.py` about 250 lines is the worked example). Cases come from "a small golden set you own or, for most sections, **from the memory's own data**".

**Doors.** "A **door** is the path a memory is reached through and the text that comes out of it". The door section scores the delivered text, not retrieval: "a fact that retrieval found but the cut removed does not help the model." ADE doors: `voice` (cut at 2,400 characters, card first), `agent` (MCP context plus top semantic hits, no cut), `raw`. A `two-step` door (brief then details within the same budget) is measured with a fixed rule (`adebench/twostep.py`).

**Sections (README table, lines 33-42).**
| Section | Weight | What passes (paraphrase, key phrases quoted) |
|---|---|---|
| door | 25 | expected words inside the text "the client actually receives" |
| cards | 15 | entity card exists, dated, within limit (default 900 chars), contains owner's corrections; aliases lead to canonical card |
| updates | 10 | "Facts get **updated**, not accumulated": id-less write of 9000 after 8000; door serves 9000 and never 8000; unrelated fact survives; restating adds no copy. Without `write_fact`, the adapter's own sandbox test scores. Historical trace "reported, never scored" |
| time | 10 | every memory reaches the model with its age as a leading bracketed date; day filter; imported memory keeps its original date |
| live_state | 10 | canary served (write-to-serve latency p50/p95 reported); overwrite serves new value only; two quick writes settle on the second |
| abstention | 10 | invented entities: no card, no keyword hits, "the memory says it does not know" (checks retrieval output, not the final sentence) |
| file_search | 10 | real function names from a repo: right file in top 5 |
| graph | 10 | every carded entity has edges; no orphan fact nodes |

Report-only: `health` (including index coverage; "the reference Brain ran four days with 15 episodes indexed out of 2,689 while the score stayed at 95"), `doors` (latency, characters per door), `census`, `write_back`.

**Scoring rules.** ERROR never earns ("a broken service never looks like a good one"); SKIP leaves the score; a section with no evidence is "not measured" and its weight leaves the denominator, reported as `score / measured weight` plus coverage. Whole-token matching ("`8766` does not match `18766`"); `*` suffix for prefixes. Deltas only against a run with the same setup fingerprint (adapter, door, golden set, sections, cut, sandbox test, repo, weights, pressure). Tests guard "an error counted as a pass, a failed read counted as missing data, a missing feature counted as a success, a substring counted as a match".

**Margin and pressure.** Each pass reports its margin to the door budget; warning under 300 characters. `--pressure N` inserts N characters of competing payload before the cut; `median` / `p95` / `max` resolve from a callwitness census of MCP tool response sizes. "Budget spent on nothing" (chars before the answer, repeated chunks) is reported; no precision score.

**Judge.** None in the scored harness ("No LLM runs in the harness"). An LLM-judged LongMemEval-S side study lives in `examples/longmemeval/`.

**Golden set format.** `{"question": ..., "expected": [["8766"]], "entity": "brain", "forbidden": [["1.3.0"]], "validated": true}`; `expected` is a list of groups (all required, alternatives within a group). Rules: "deterministic expectations (ports, versions, names, dates) rather than paraphrases, and never fix a failing case by loosening the expectation". The benchmark warns if invented abstention entities are stored anywhere in the memory (the Brain once learned its own benchmark answer from a note about the benchmark).

**Synthetic set.** 8 door questions (e.g. "Which version of MailBridge is installed for the mailbox?" expected `1.4.2`, forbidden `1.3.0`; "What is the owner's phone number?" whose fact is deliberately absent) and 4 abstention questions ("What is the Zarpetta module?", "Who is Ottavio Brambillesco?", "Which port does the Fulmicotone service use?", "What does the calendar plugin Girandola do?"). Every memory fails the same two door questions by design.

## Numbers
All from README.md at the pinned commit unless noted. Denominator = points measured.

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Synthetic reference adapter | "90.0 / 100, 48 PASS · 5 FAIL · 0 ERROR · 0 SKIP" | none | in-process synthetic memory with 5 planted defects; CI re-runs | defects deliberate |
| Dakera total | "96.9 / 100" | gbrain "86.9 vs gbrain's 75.4" on 90 shared points | synthetic set, pinned Dakera config (sentence decomposition off) | default config "non-deterministic run-to-run" |
| Dakera updates probe | "passes it 3/3" | none | id-less write_fact; engine forms `Supersedes` edge at "≥0.92 cosine, strictly later" | its door STALE pass is "a door result, not supersession" (top_k=8) |
| ADE Brain total | "93.8 / 100" | none | synthetic set loaded into an empty Brain; cards by gemini-3-flash-preview; decay off | maintainer's own system; abstention 10/10 "after a change" (9.2 before) |
| ADE Brain updates / latency | updates 10 / 10; "Replacement visible in 93 ms, write to serve 106 ms" | none | same | |
| gbrain total | "75.4 of the 90 points" | none | gbrain 0.50, PGLite, ollama:nomic-embed-text, run 28 Sep 2026 | file_search not measurable |
| gbrain sections | door 18.8 / 25; updates 3.3 / 10 ("10 reads with both"); abstention 8.3 / 10; write-back "2 of 2 poisoned" | earlier run 73.8 / 80 on 13 Sep | same | earlier run predates update probe |
| Memoose total | "68.3 of the 90 points" | none | engine only (no model-run skills) | updates via sandbox test "2 of 4" |
| Memoose sections | door 18.8 / 25; abstention 5.8 / 10; time 5 / 10; live_state 8.8 / 10; cards 15 / 15; graph 10 / 10 | none | same | retired sentence still served from lexical chunks |
| Aionforge total | "51.8 of the 65 points" | gbrain "50.4" on the same 65 | Aionforge 0.4.0, gemini-embedding-001 via shim | forgetting enabled with lowered floors |
| Aionforge sections | updates 6.7 / 10 ("23 reads with both values"); live_state 10 / 10, write-to-serve "452 ms p50, 483 ms p95", overwrite "455 ms"; abstention 8.3 / 10; time 8 / 10; write-back "2 of 2 poisoned" (448 ms) | none | same | supersession only if client passes a `supersedes` id |
| Hindsight total | "36.2 of the 55 points" (README later: "36.3 vs gbrain's 40.4" on the same 55) | gbrain 40.4 | MCP 0.10.1, extractor gemini-3.5-flash-lite (documented gemini-3.5-flash returned 503), recall defaults, no `min_scores`; reference.md: 10 PASS · 9 FAIL · 0 ERROR · 5 SKIP | 36.2 vs 36.3 inconsistency in the README; live_state not run |
| Hindsight abstention | 6.7 / 10; "0 of 4 abstentions" as deployed; no-match query "returns the whole bank at 1e-5, 28 memories" | with `ADEBENCH_HINDSIGHT_MIN_SCORE=0.1`: "abstention 4 of 4", total "36.5 / 55" | same | the floor drops a gold fact scored 0.006 ("Where does the owner live?") |
| Hindsight updates / time / write-back | updates 3.3 / 10 ("20 reads with both", "three copies", replacement 561 ms); time 7.5 / 10; write-back "0 of 2 poisoned" | none | same | extractor rewrote the imported date |
| One-call vs two-step door | "23/25" one-call vs "17/25" two-step whole details, "18/25" capped at 300; under census p95 "19/25 against 8/25"; gbrain "18/25 to 20/25" | each other | budget 2,400, reference memory | owner's real memory, n not stated |
| Index coverage defect | "15 episodes indexed out of 2,689 while the score stayed at 95" | none | reference Brain, four days | shows door-only scoring can miss storage defects |
| LongMemEval-S retrieval strict@5 | "88.7% (417/470)" BM25 + vectors | BM25 "82.6% (388/470)"; keyword Italian stopwords "64.5% (303/470)" | 470 non-abstention questions, no LLM (examples/longmemeval/README.md) | ADE Brain only |
| LongMemEval-S end to end | gemini-3-flash-preview "79.8% (399/500)"; gpt-6-astra "88.4% (442/500)" | when retrieval complete: "86.6% (361/417)", "96.6% (403/417)" | 500 questions, judge gpt-4o-2024-08-06 | |
| Judge swap, same 100 answers | gemini 83 -> 85; astra 89 -> 85; gpt-oss:20b local 67 (GPT-5.1 only) | judge GPT-4o vs GPT-5.1 | stratified 100 | "A number without its judge is not a result." |
| Pre-registered kill criterion | "67/100, below 70, the kill criterion fired" | threshold 70 / 80 in KILL_CRITERION.md | local gpt-oss:20b, RTX 4050 6 GB, median "48.4 s" per answer | 5 empty answers from reasoning filling 32k context |

## Mechanism details you could implement
- Golden case schema with `expected` groups plus `forbidden` retired values; a text carrying both fails as `STALE`. For PDLC: forbidden = superseded decision values, old API versions, closed ticket states, reverted requirement text.
- Id-less update probe (write new value without naming the old; check old never served, sibling fact survives, restatement not duplicated). This isolates whether supersession is inferred by the memory rather than supplied by the client; Aionforge only supersedes when the client passes a `supersedes` id.
- Write-back probe: starve the door (pressure equal to budget), write a degraded answer through the memory's normal write path, ask again without pressure; fail if the degraded answer reaches the door or the true answer disappears. Default `ADEBENCH_DEGRADED_ANSWER` = "I have no record of that. You asked: {question}", 2 questions, 10 s settle.
- Score the delivered text at a declared budget, report margin to the cut and pressure levels; keep coverage and SKIP explicit so a partial run never reads as a full score.
- Setup fingerprint on every run; deltas only between identical setups.
- Keep invented abstention entities out of the memory, and warn if they appear (the benchmark contaminating its own subject).

## Limitations, caveats, counter-evidence
- Tiny case counts: 8 door questions (each about 3.1 of 25 points) and 4 abstention questions; the update probe is 3 checks. By B21, a zero-failure result on 3 checks bounds nothing useful.
- Totals are over different denominators (55, 65, 90, 100); the README's own rule is comparability only with the same door kind and the same coverage.
- Independence: the harness grew around the maintainer's ADE Brain (sections chosen "from reading the reference Brain"), which then scores 93.8 after fixes found by the benchmark; external systems were configured by the maintainer, some with non-default or substitute settings (Hindsight extractor model, Dakera pinned decomposition, Aionforge lowered forgetting floors).
- Abstention checks retrieval output, not the final answer; the README says so. The forbidden check is presence-based: "It was 8010, now it is 8766" fails even though history is labelled.
- No Mem0, Zep, Letta or supermemory runs; no Nemp. The "What should be added?" list still asks for "an adapter for a real memory system that is not an ADE Brain" although six exist (stale list, inference).
- Personal-assistant domain: short facts, voice cut; nothing on long structured artifacts, multi-hop trace links (implements, verifies, supersedes across documents) or build-time reads (inference).
- No instruction-bearing content aimed at AI agents was found in the files read. The source post could not be fetched (HTTP 402).

## Takeaways for tuning a memory stack
- Adopt the three stale probes (forbidden value in delivered text, id-less update, write-back of a degraded answer) into our PDLC benchmark scope; they are cheap, deterministic and separate mechanisms that chat benchmarks conflate.
- Directional evidence that write-time supersession matters for served staleness: the systems without a write-time supersede step served both values (gbrain 10 reads, Aionforge 23, Hindsight 20), Dakera with a similarity-gated `Supersedes` edge passed 3/3. Whole-system comparison on 3 checks, so it supports B3 only weakly.
- A relevance floor trades abstention for recall: Hindsight at min score 0.1 went from 0 of 4 to 4 of 4 abstentions but lost a gold fact scored 0.006. Keep ranking and admission separate (B11).
- Guard the write path against storing absences: do not write "no record of X" exchanges as facts, or rank them below evidence-bearing facts.
- Report index coverage and storage health alongside door scores; a door score can stay high while indexing silently fails.
- Always name the judge with any LLM-judged number.

## Open questions
- What is Nemp (the system the post wants to test)? Not stated in the repo.
- Would the Dakera 0.92 cosine supersession threshold hold on long PDLC artifacts where the new decision is phrased differently from the old? Not tested.
- How do Mem0, Zep, Letta and supermemory do on the id-less update and write-back probes? No data.
- Would the maintainer accept a PDLC golden set (engineering artifacts, trace-link questions) as a second public set? Unknown.

## Grading and labels
- Directness: high, primary repo and committed reports at a pinned commit.
- Control: medium, same harness and cases, differing coverage and per-system configuration.
- Independence: low, maintainer-built around own system, all runs by the maintainer.
- Reproducibility: medium, MIT and CI-pinned synthetic reference; external runs depend on live services and LLM extractors.
- Applicability: medium, engineering-flavoured facts and stale checks, but tiny n and personal-assistant framing.
- Pillars: R6 primary; R2 (supersession, update semantics), R8 (write-back self-poisoning), R3 (door budgets, relevance floors) secondary.
- Stage: evaluation.
- Tags: see frontmatter.
- Beliefs: supports B3 (weakly: memories with write-time supersession pass the id-less update probe, those without serve both values; whole-system, 3 checks). Supports B11 (a score floor that enables abstention dropped gold evidence). B5 and B6 not affected (no consolidation or decay on/off; the Brain ran with decay off). Would create: write-back self-poisoning belief (R8/R2) and judge-sensitivity belief (R6), wording in frontmatter. No contradiction.

## Origin chain
X post 2104675152235528690 (@0xdudoshi, self-described maintainer; not re-fetched, HTTP 402) -> https://github.com/adecubed/adebench @ 5a2b2db10958b5a79ee6b802957f87e9912a93a6: README.md (sections table lines 33-42; scoring lines 58-85; per-system results lines 225-495; synthetic reference lines 497-516; golden set lines 563-603), examples/hindsight_report/reference.md (case counts), examples/longmemeval/README.md (retrieval, reader and judge tables), examples/synthetic_data/cases/*.json (n cases). Independence: benchmark author, reference-system author and runner of all external systems are the same party; no vendor-confirmed runs.
