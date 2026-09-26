# Research restart — September 2026

**Date:** 2026-09-25. **Predecessor:** the January–February 2026 research pass in `docs/research/*.md` (files dated 2026-02-07 to 02-13) and the gap analysis in `docs/replication/2026-09-25/` (branch `codex/adr-lld-gap-analysis-2026-09-25`).

## Why a restart

The February research grounded ADRs 0001–0017 in the memory and context-graph literature as it stood then. Since then: a separate codebase has moved ahead (ADRs 0019–0030: LLM gateway, evaluation suite, API v1 contract, grants, GDPR crypto-shred, tenant configuration, disaster recovery); the memory-systems literature has produced a provenance-first category that Engram anticipated but has not fully implemented; recursive self-improvement has emerged as a framing for what a memory layer is *for*; a typed-decision model (Jev) offers a new place to put judgments; and there is a new product requirement — a knowledge/memory layer for the product development lifecycle (requirement → HLD/LLD → tickets → PR).

This pass digests those inputs and states a path forward. It does not change code.

## Files

| File | What it is |
|---|---|
| [paper-digests.md](paper-digests.md) | One entry per paper/article received, with an adopt / adapt / context verdict. **Append here as papers arrive.** Current entries: D1 RSI taxonomy; D2 Mendel Gödel Machine; D3 Beacon (Asymptote Labs); D4 supermemory on Jev in memory pipelines; D5 Instinct memory teardown; D6 Just-in-Time Memory (Salesforce); D7 "Self-Improving Agents" daily brief (2026-09-25); D8 memory-stack evidence bundle (supersedes D7 where they differ; Jev-Mem, REALM, EvoSkill, RRSI read in full there) **plus the v2 addendum**: jevmem save gate, consolidation-as-phase (T4), staleness/provenance (T5), planner + decider. Still queued: CL-Bench. |
| [discovery-plan.md](discovery-plan.md) | Prerequisites P1–P5 and hypotheses H1–H10, each with setup, metric, kill criterion and what a pass unlocks; ground rules from RRSI; sequencing. |
| [evidence/](evidence/README.md) | Systematic evidence catalogue behind the daily brief, **v2** (7 trends, 38 items; 5 papers read in full, 6 repos at pinned commits, 54 transcribed images): synthesis by design decision, ledger, 30 source notes. Digested as D8 and its addendum. |
| [memory-research-landscape.md](memory-research-landscape.md) | Survey of agent-memory, retrieval, benchmark, ontology-enforcement and SE-agent-memory work since March 2026, each item mapped to an Engram component. Includes the RSI memory/skill systems. |
| [rsi-positioning.md](rsi-positioning.md) | Engram in the RSI taxonomy: which tenets to plug in (six, ranked), which not to, and a minimal implementation order. |
| [jev-typed-decisions.md](jev-typed-decisions.md) | Verified facts about Jev / TypeSafe System One; a plug-in map to Engram's judgment points (six async gates A1–A6 first, retrieval-side B0–B5 second); field evidence; rollout and risks. |
| [judgment-points-catalogue.md](judgment-points-catalogue.md) | Every rule, threshold, embedding or LLM decision in the current code, with inputs, output shape, cost, failure behaviour and whether a receipt is kept. Reference for the two documents above. |
| [write-read-path-scale.md](write-read-path-scale.md) | Hop-by-hop write and read path, API surface, ADR-0018 claims vs code, three confirmed defects, ten ranked risks. |
| [pdlc-memory-layer.md](pdlc-memory-layer.md) | First take on the PDLC knowledge/memory layer: ontology extension, retrieval modes, write-side integrations, evaluation, open questions. **Preliminary until the grounding document is received.** |
| [pdlc-grounding/](pdlc-grounding/jetstream-reference-transcription.md) | Transcription of the grounding document ("Nitin jetstream artifacts reference") as it arrives, with a first read of what it changes. **Partial: §0, Part 1, Part 2 (contracts C1–C11, Outer Loop, seams), Part 3, Part 4 §4.1–4.2 received 2026-09-26 — **note the name collision: "Engram" in the programme is a different system**; the rest of the C6 proposal, the 11 ontology dimensions and the harness retrieval comparison still to come.** |

## How the analysis was produced, and how far to trust it

- **Code findings** come from static reading of branch `feature/autoresearch-eval-scoring` at `9df84ed` (application source identical to `dev`), by code-analysis agents. Three defects (bulk-ingest payload loss, dead RediSearch index, no-op Redis retention) were re-verified by hand and are marked *confirmed*; the rest are marked *reported*. Nothing was run against live Redis/Neo4j.
- **Literature** comes from search-engine excerpts of arXiv abstracts and directly fetched GitHub pages; arxiv.org and huggingface.co are blocked from the analysis environment. Numbers are as reported by authors. Dates are arXiv submission dates as quoted.
- **Jev facts** come from verbatim Markdown mirrors of TypeSafe's docs (fetched 2026-09-23) and TypeSafe's own GitHub repositories; the vendor sites themselves were blocked. Each fact is labelled *vendor states* or *third-party*.
- **The February research map** used to avoid repetition: all 29 real files (one, `llm-extraction-techniques.md`, is a committed absolute-path symlink and is broken outside the author's machine) assume an SMB-merchant support-agent domain; nothing covers software-engineering artefacts; the extraction research already anticipated two-tier cheap-classifier → escalate, NLI grounding checks, and LLM arbitration for entity matching and Mem0-style ADD/UPDATE/SUPERSEDE.

## The path forward, in order

The documents converge on one sequence. Each step is small, additive to the frozen contracts, and unblocks the next.

1. **Fix the three confirmed defects and the tenant-blind entity resolution** ([scale](write-read-path-scale.md) D1–D3; [catalogue](judgment-points-catalogue.md) headline 6). Until then throughput, retention and multi-tenancy claims are not defensible, and bulk-ingested sessions have no content to extract.
2. **Introduce receipts**: a retrieval receipt (which memories were served for which query/task) and a decision receipt (state digest, battery version, model, distributions, threshold, outcome) as ledger events. This one primitive is required by the RSI feedback loop, by the Jev layer, and by the provenance literature (Eywa, MemIR, MemTX). Today almost no decision in Engram leaves one.
3. **Make memory updates explicit and gated** ([RSI](rsi-positioning.md) T1): proposal event → gate → committed version, with MemTX-style node state and TARL-style actions. Put the independent judge for extraction acceptance, entity merges, supersession and deletion behind the `ports/decision.py` interface, with Jev as the first adapter ([Jev](jev-typed-decisions.md) A1–A6) and the current rules as the fallback. Supersede on two signals and never delete; add per-item provenance (source class, recorded time, reason) so that a staleness audit and an injection gate on served memory (A6, B5; discovery H10) have something to act on.
4. **Stand up procedural memory** ([RSI](rsi-positioning.md) T3; [digest D2](paper-digests.md)): a stable `task_key` on events; Workflow induction from Episodes with per-task outcome records; comparative refinement (same workflow across tasks, sibling success on the same task); multi-parent SUPERSEDES that keeps sibling versions; a negative-evidence node; a "failed-task pool" pre-action retrieval mode. This is the RSI layer and the core of the PDLC product. Pair it with a **read-time curate step** over raw event payloads for task-start requests ([digest D6](paper-digests.md)): the graph selects the evidence, an LLM synthesises a task-conditioned briefing, the briefing is ephemeral, its receipt is a ledger event. Write-time extraction and summaries become retrieval cues and cached curations, not the only read surface.
5. **Replace the evaluation harness** ([landscape](memory-research-landscape.md) §3): remove label leakage, import the real scoring, freeze the judge, add a held-out split and paired-stats gating; run DreamBench-SWE, ForgetEval, MemOps, and MemDelta's one-variable protocol before publishing any graph-vs-vector number.
6. **PDLC ontology and adapters** ([pdlc](pdlc-memory-layer.md)) once the grounding document settles the open questions. Do not build 20 harness collectors: Beacon's OTel-normalised JSONL ([digest D3](paper-digests.md)) is a candidate ingest source; Engram's value is after capture. Put the retrieve-or-not gate ([Jev B0](jev-typed-decisions.md)) in the harness adapters.
7. **Measure Consumer 4 before tuning it** ([discovery H9](discovery-plan.md)): no source anywhere reports consolidation on vs off, and the only number is negative. Until H9 runs, summaries are cache, not a read surface.
8. **Scoring refinements** ([landscape](memory-research-landscape.md) §8 item 7): per-edge-type volatility, co-activation strengthening, reinforce-on-used, silent maturation — contained changes to `scoring.py`, measured with the fixed harness.

Items 1–3 are independent of the PDLC requirement and of Jev's commercial terms; they are the foundation whichever direction is chosen next.

## Branch note

These documents are written on `claude/wonderful-ramanujan-2cxghz` (currently identical to `main` plus this folder). The newest application code is on `feature/autoresearch-eval-scoring` (= `dev` + evaluation tooling); `main` carries an older version of the same features and diverges from `dev` in 8 frontend and 3 backend files. Reconciling `main` and `dev` is a prerequisite for step 1 and is documented in the gap analysis branch.
