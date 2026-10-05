---
schema_version: 1
artifact_id: N-20260928-10
artifact_type: note
producer: triage
run_id: triage-20260928T074501Z-535d
created_at: 2026-09-28T07:59:03Z
input_refs: [{"artifact_id": "post:2104328430598906300", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:spinsirr.github.io/blog/why-we-do-not-extract-facts-by-default
claim_cluster: url:spinsirr.github.io/blog/why-we-do-not-extract-facts-by-default
feeds: ["memory"]
primary_source: https://spinsirr.github.io/blog/why-we-do-not-extract-facts-by-default/
source_commit: 4976fa162a29e9a082a1f53f3276f86c622b164b
strength: repo-pinned
pillar_primary: R2
pillar_secondary: ["R3", "R6"]
memory_stage: ingestion
priority: 4
tags: {"mechanism": ["fact extraction", "session summarisation", "raw evidence retention"], "workload": ["chat memory", "LongMemEval-S"], "lifecycle_stage": ["write", "consolidation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: a same-reader, same-retriever, same-judge A/B on 500 questions with the runner committed", "control": "medium: one variable (corpus representation) changed, but one extractor, one run, and the headline source run used type-aware reader prompts with no matched static-prompt fact-sheet run", "independence": "medium: builder of Lore (CoreSpeed) measuring its own design choice, but on an external benchmark with official judge prompts", "reproducibility": "medium: runner and extractor scripts pinned at a commit; reader and extractor model names not stated in the blog", "applicability": "medium: chat memory, not engineering artifacts, but the extract-then-discard question is exactly our write path"}
beliefs_affected: {"supports": ["B16", "B5"], "contradicts": [], "would_create": ["Session-level retrieval recall does not measure whether answer-bearing detail survived write-time extraction; score the evidence handed to the reader"]}
claim_correction: none (the post's numbers match the blog table; the blog adds that recall@10 barely moved, 98.98% vs 98.69%, and that the loss was steepest, 100% to 73.2%, on questions about what the assistant said)
---

# Lore: "Why we do not extract facts by default" (fact sheets vs source sessions on LongMemEval-S)

- **URL:** https://spinsirr.github.io/blog/why-we-do-not-extract-facts-by-default/
- **Type:** builder writeup, backed by a repo commit
- **Author / org:** Spencer Zhao (cofounder, CoreSpeed); system: Lore, https://github.com/corespeed-io/lore (MIT)
- **Date:** blog dated 2026-09-27; experiment commit `4976fa162a29e9a082a1f53f3276f86c622b164b` (2026-08-26T22:07:00Z, "feat(benchmark): LongMemEval end-to-end answer grading and facts corpus")
- **Retrieved:** 2026-09-28. Blog read via WebFetch and raw HTML; repo HEAD cloned at `f1e60b5135b99de2fab85ccae3e9002f2d4b161f` (2026-09-28 00:21:58 -0700, "Merge pull request #129 from corespeed-io/feat/memory-link-api") into `repos/lore`; experiment commit message read through the GitHub API. The fact-sheet numbers are not in any file at HEAD (only the blog and the commit message carry them).
- **Cited by evidence:** @zhao_spenc, 2026-09-27, https://x.com/zhao_spenc/status/2104328430598906300 ("In 500 LongMemEval questions, fact sheets cut reader input ~10x but dropped answer accuracy from 94.2% to 87.8% with the same reader.")
- **Relevance to a memory stack:** high. It is a clean, one-variable measurement of the write-time "extract facts, index the summary" design that Mem0-style stacks default to, and it shows why retrieval recall alone hides the loss.

## TL;DR
- On LongMemEval-S (official cleaned split, 500 questions, one isolated workspace per question), replacing each session with one extracted "fact-sheet Memory" cut reader input from about 28k to about 2.8k tokens per question and dropped answer accuracy from 94.2% to 87.8% (32 fewer correct answers).
- Retrieval recall@10 hardly moved (98.98% vs 98.69%): the right session was still found, but the detail the question needed had been removed at write time. Session-level recall cannot see this failure.
- The steepest loss was on questions about what the assistant said: 100% on source sessions vs 73.2% on fact sheets.
- A cheaper point exists without extraction: 5 source sessions instead of 10 scored 90.2% at about 14k tokens, which beats fact sheets on accuracy at 5x their tokens.
- Lore's design conclusion: source evidence stays canonical; an extracted summary is a derived view and extraction is an explicit option, not the default write path.

## What it claims / describes
**Experiment (blog, "We tested that boundary in Lore" and following paragraphs; commit 4976fa1 message).**
1. Corpus A: the original LongMemEval-S conversation sessions, each indexed as a Memory.
2. Corpus B (`{questionId}#facts`): "an extractor distills each indexed session Memory into one compact fact-sheet Memory (same benchmarkKey, tripwires replicated, embeddings drained through leased maintenance), with original-content passthrough tagged extractorFallback on provider content-policy blocks" (commit message).
3. Held fixed: retrieval algorithm ("hybrid retrieval under RLS", embeddings `gemini-embedding-2 @1536` per the commit message), reader ("a flash-class reader", commit message; exact model not stated), top-10 evidence, and the judge ("the official upstream QA judge prompts reproduced verbatim (pinned to xiaowu0162/LongMemEval@d6dc8b50, temperature 0, yes/no labeling, abstention template for _abs questions)").
4. Reader prompt: "The reader used instructions selected from the benchmark's question type." A separate source-session run with one static prompt scored 93.8%.
5. Retrieval target for recall@10 is the answer-bearing session; a fact sheet keeps its source session's identity, so it counts as a hit even when the needed detail is gone.

**Design consequence (blog, closing section):** "Lore therefore treats a canonical Memory as an intentional knowledge record. Interaction messages and document fragments can be retained as immutable Observations. An authorized actor can write a Memory directly, or submit a proposed Memory for its owner to review. A proposal is not searchable canonical Memory until ac[cepted]..." and "automatic fact extraction a deliberate option rather than Lore's default write path". The commit notes "Lore v1 still excludes automatic consolidation."

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| answer accuracy, fact sheets top 10 | 87.8% | 94.2% (source sessions top 10) | LongMemEval-S, 500 q, same retriever/reader/judge (blog table) | one run, one extractor; 94.2 used type-aware reader prompts |
| reader input per question | ~2.8k tokens | ~28k tokens | same | "roughly 90%" saving |
| retrieval recall@10 | 98.69% | 98.98% | session-level target | recall is blind to detail lost inside a hit |
| correct answers lost | 32 of 500 | n/a | blog text | |
| assistant-statement questions | 73.2% | 100% | blog text | category n not stated |
| source sessions, top 5 | 90.2% at ~14k tokens | 94.2% at ~28k | blog text | cost/quality point without extraction |
| source sessions, static reader prompt | 93.8% | 94.2% (type-aware) | blog text | no matched static-prompt fact-sheet run |
| cross-workspace isolation | 0/500 leaks | n/a | commit message | |

## Mechanism details you could implement
- Keep two corpora keyed to the same source id: canonical source records and derived summaries. Score answers from each with the same reader and judge; never only score retrieval recall on the source id, because a derived record inherits the source's id and "hits" while missing the answer.
- Measure "evidence sufficiency at the reader": whether the text handed to the reader still contains the answer, not whether the right parent was found (the blog links a separate conflict-retrieval study with the same lesson).
- Treat extraction as a proposal: extracted Memories are reviewed or owner-accepted before becoming searchable canon; raw interactions are retained as immutable Observations.
- Budget knob that preserves evidence: reduce k over source records (10 to 5 sessions) before switching to summaries; in this run it lost 4.0 points instead of 6.4 at 5x the tokens of fact sheets.
- Extractor fallback: when the extractor is blocked, pass the original content through and tag it (`extractorFallback`) so the corpus is complete and the fallback rate is countable.

## Limitations, caveats, counter-evidence
- "The 6.4-point gap belongs to this dataset, this fact-sheet extractor, and this reader configuration." No stronger-extractor sweep, no matched static-prompt fact-sheet run, no product-usage study (blog, final paragraph).
- Reader and extractor model identities are not stated in the blog ("flash-class reader" in the commit). The extractor prompt is not quoted.
- Single run; no seeds or intervals. A 6.4-point gap on 500 questions is well outside the 0.4-point static-vs-typed prompt difference, but no uncertainty is reported.
- LongMemEval is chat memory; our artifacts are long, structured engineering documents where a fact-sheet extractor might lose more (tables, exact values) or less (inference).
- Vendor of a raw-evidence memory product measuring against the design it rejects (inference: incentive to publish this result).

## Takeaways for tuning a memory stack
- Do not make write-time extraction the only durable copy. Keep source evidence; serve summaries as a derived, optional view.
- Add a reader-level evidence-sufficiency metric to any memory eval; retrieval recall on parent ids will hide extraction loss.
- If context budget is the constraint, first try smaller k over raw sources, then summaries, and measure both at matched tokens.
- Questions about "what the assistant/agent said or decided" are where extraction hurts most here; for engineering agents that maps to "why did we decide X" questions (inference).

## Open questions
- How big is the loss with a stronger extractor or with type-specific fact schemas (decisions, constraints, numbers)?
- Does the gap persist at matched reader tokens (fact sheets with larger k vs source with smaller k)?
- What is the per-category breakdown beyond the assistant-statement category?

## Grading and labels
- Directness: high, it shows the measurement, not a description.
- Control: medium, one variable changed, but prompts differed between the headline source run and the fact-sheet run was not re-run with the static prompt.
- Independence: medium, CoreSpeed measures its own design choice on a public benchmark with the official judge.
- Reproducibility: medium, scripts pinned at commit 4976fa1; models partly unstated.
- Applicability: medium, the write-path question is ours; the data is chat.
- Pillars: R2 primary (write-time extraction as a durable state change), R3 and R6 secondary. Memory stage: ingestion. Priority 4 (LongMemEval, our PDLC benchmark should include a reader-level sufficiency metric).
- Beliefs: supports B16 (raw history over distilled representations, here for facts rather than skills); supports B5 (aggressive summarisation measured negative; this is a second negative measurement); would create "session-level recall hides extraction loss".
- Contradiction rows: none.

## Origin chain
- Post 2104328430598906300 (@zhao_spenc, the author) -> blog https://spinsirr.github.io/blog/why-we-do-not-extract-facts-by-default/ (results table and following paragraphs) -> commit corespeed-io/lore@4976fa1 (message and files `scripts/benchmark-longmemeval-e2e.ts`, `scripts/benchmark-longmemeval-extract-facts.ts`) -> this note.
- Independence: same author for post, blog and repo. Dataset LongMemEval-S (xiaowu0162/LongMemEval@d6dc8b50) is shared with Hindsight, REALM, HivemindOS and other notes; judge prompts are the upstream ones.
