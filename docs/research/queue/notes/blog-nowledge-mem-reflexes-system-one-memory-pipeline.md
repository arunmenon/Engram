---
schema_version: 1
artifact_id: N-20260930-12
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105136922482094205", "file_id": null, "sha256": null}, {"artifact_id": "post:2105135876921794822", "file_id": null, "sha256": null}, {"artifact_id": "post:2105180332068884917", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:nowledge-labs.ai/blog/reflexes-for-memory
claim_cluster: url:nowledge-labs.ai/blog/reflexes-for-memory
feeds: ["memory", "decision"]
primary_source: https://nowledge-labs.ai/blog/reflexes-for-memory
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R2", "R4"]
memory_stage: write_gate
priority: 1
tags: {"mechanism": ["question-list decisions", "decision before generation", "batched questions", "shadow mode", "fail-open on missing answer", "temporal intent for rerank"], "workload": ["personal and work memory product", "Chinese and English"], "lifecycle_stage": ["write_gate", "ingestion", "reranking", "linking"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium", "control": "medium", "independence": "low", "reproducibility": "low", "applicability": "medium"}
beliefs_affected: {"supports": ["B11", "B14"], "contradicts": [], "would_create": ["At a write gate most of the saving attributed to a System One model comes from restating the review as separate typed questions and batching them, not from the model swap", "Open-weight encoder decision models (Laya included) did not meet a chat-model quality bar on memory decisions in Chinese and English"]}
claim_correction: The posts say Nowledge Mem is now optimized with System One decision models; the blog says about 85% of the modelled saving comes from workflow changes and batching unrelated to Jev, measured savings were roughly 10% to 19% per thread, candidate review still runs in shadow mode, and Jev's own accuracy figures are withheld at the vendor's request.
---

# Giving a Memory System Reflexes (Nowledge Mem blog): System One decisions across a shipping memory product, with Jev (TypeSafe), Laya and Dohnuts

- **URL:** https://nowledge-labs.ai/blog/reflexes-for-memory (also linked from the X article https://x.com/i/article/2105132677699682304, which was not fetchable)
- **Type:** vendor blog (first-hand builder writeup)
- **Author / org:** Wey Gu, Nowledge Labs (Nowledge Mem: Vault desktop app and Cloud)
- **Date:** 2026-09-28
- **Retrieved:** 2026-09-30, page as served (local copy: repos/_src_nowledge_reflexes.html). No version identifier on the page.
- **Cited by evidence:** https://x.com/wey_gu/status/2105136922482094205 (@wey_gu, author), https://x.com/nowledgelabs/status/2105135876921794822 (@nowledgelabs), reply https://x.com/rediasChao/status/2105180332068884917 (@rediasChao, asks about NER). Quoted post https://x.com/NowledgeMem/status/2105134977210056804. Memory digest of 2026-09-30 ("Adoption on the memory path").
- **Relevance to a memory stack:** high. A named memory product reports where it put a System One model in its write and read paths, what it kept in shadow, what it measured, and what open-weight models could not do. This is CTO priority 1 (System One across the memory stages) and priority 2 (open-weight comparison).

## TL;DR
- Nowledge Mem shipped "Fast decisions": a configurable decision service (TypeSafe Jev with the user's own key, or a managed configuration) used for conversation screening, an unsaved-knowledge check before extraction, deduplication, write-quality checks, type classification, and temporal interpretation in deep search. Candidate review runs in shadow mode only.
- The measured result is mostly about question shape, not the model: with the same chat model (Kimi k3, 40 candidates), restating the review as a list of separate questions with answers only raised overinterpretation F1 from 0.27 to 1.00 and long-term retention F1 from 0.83 to 1.00 at lower cost.
- Cost model for a heavy user: original process 100, same model with decisions before generation plus batching about 37, with Jev about 26. "about 85% of the savings come from changes to the workflow, including batching unrelated to Jev." Small integration tests showed "roughly 10%-19% lower cost per conversation thread" (the source writes the range with a dash).
- Open-weight check: three encoder decision models (Laya, Von, Verdict) and Dohnuts (Qwen3.5-0.8B with LoRA and a scoring head) were tested. "no local model met the earlier requirement in both Chinese and English on any task."
- Jev's own accuracy is not reported: "At the Jev team's request, we cannot disclose Jev's own performance figures."

## What it claims / describes

**The interface.** A `DecisionClient` lets Jev and chat models answer the same set of questions. Each decision is "individual questions, each with explicit criteria and allowed answers", several questions about the same material go in one call, and work that needs generated text (the source lists memory content, summaries and entity names) "stays with the LLM." The exact question wording, question types (Noul, Choice, Score) and thresholds are not stated.

**Decision before generation.** "decision tasks accounted for more than half the calls but only about a quarter of the cost. Most of the spending went to generation: extracting memories from conversations, extracting graph information, and backfilling data." The change is to screen content before LLM extraction. Screening needs two judgments: "the new information is worth keeping long term, and it has not already been saved."

**Safety rules around the gate (stated design rules).**
- Dedup must compare against memories that were actually written: "A decision appearing in a summary does not mean it has been written to the memory store."
- Fail open: "If the decision call times out or fails, we continue through the original extraction process. A missing answer cannot be a reason to skip the content."
- Asymmetric thresholds: "a candidate accepted by mistake can still be caught by deduplication or write-quality checks. A candidate rejected by mistake never reaches the save process... One confidence threshold for every judgment will not do."
- Audit chain: "We have to connect what the model saw, which answers the program acted on, and what was finally written."

**Retrieval.** The existing chat model still does general intent analysis; the decision model adds temporal interpretation. In Memory Deep Search, if a decision service is configured, it is also tried for reranking "when it identifies temporal intent and returns a usable result within the time budget. Otherwise, we use the existing reranker." A model-inferred time range "only influences ranking and is returned as a suggested filter. Only filters the user explicitly provides are enforced." Default fast search does not include the decision step; the page says that in the team's tests retrieval finished before the decision model's answer arrived, so the answer could not help ranking (paraphrase of the section "Memory retrieval").

**What is running (table in section "What is running today", checked in the raw page).**

| Stage | Current use (verbatim) |
|---|---|
| Decide whether a conversation is worth extracting memories from | "Decision models are in use on desktop and Cloud" |
| Check whether new conversation content contains unsaved knowledge worth retaining long term | "Desktop uses the decision to determine whether to proceed with extraction" |
| Deduplication, write-quality checks, and type classification | "Desktop uses decision models for these judgments" |
| Review candidate memories for long-term value and source support | "Desktop records decision-model results; the original review process still decides" |
| Temporal interpretation and reranking in search | "Desktop deep search uses temporal interpretation and attempts decision-model reranking when a temporal intent is identified and the result is usable; off by default in fast search" |
| Screening before graph extraction | "Cloud uses a decision model for screening; the LLM still extracts entities and relationships" |

The fetch summary also lists tag reusability, page substantiveness and language identification as recorded only (testing); those rows were not re-verified in the raw page.

**Open-weight evaluation.** Requirement set in advance: on each task, both Chinese and English scores had to be no more than 0.05 below the chat baseline. Encoders (Laya, Von, Verdict): 290 calls each on an 8-core CPU machine with no GPU. Dohnuts (by PsiACE): Qwen3.5-0.8B with LoRA and a dedicated scoring head. Heuristic rules (word lists, minimum lengths, writing-system detection) were run through the same six tests: "The rules fell behind the chat model on all six tasks, and behind the smallest local model on four."

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Overinterpretation F1, question list with answers only | 1.00 | original review 0.27; original plus explicit confusing cases 0.42; one call per question 0.82 | same Kimi k3 model, 40 candidate memories, one run | "Those perfect scores apply only to these 40 examples"; criteria were also clarified while converting |
| Long-term retention F1, question list with answers only | 1.00 | original review 0.83; with explicit cases 0.86 | same | same |
| Relative cost of one complete candidate review | 1.00 (question list, answers only) | original 1.10; explicit cases 1.19; question list with one-sentence reasons 1.41; one call per question 2.83 | Kimi API prices at the time | experiments ran on a subscription, "these figures are not our paid bills" |
| Memory type accuracy | 0.89 | original review 0.89 | 19 candidates labelled worth retaining | an earlier gain "did not repeat in this run" |
| Cost of requiring a reason per answer | about 35% higher total cost; median latency per call roughly doubled | answers only | three tasks | no quality gain observed |
| Six questions about one candidate | 11.6 s in one call | about 50 s at p50 in six sequential calls | same chat model | amortised 8.4 s to 1.9 s per question, about 65% lower cost |
| Input caching on a reasoning chat model | each call still 6 to 33 s | | six consecutive requests, about 88% of input cached for the last five | isolated model calls, not product latency |
| Modelled monthly cost, heavy user | original 100; same model with workflow changes and batching about 37; with Jev about 26 | | 20 conversation threads and 60 memories per day | estimate; "about 85% of the savings come from changes to the workflow" |
| Measured cost per conversation thread | roughly 10% to 19% lower | original process | "small integration tests against the actual services" | the original model still handled candidate review in those tests |
| Encoder decision models (Laya, Von, Verdict) | "None of the three models met that requirement on any of the seven tasks" | chat baseline minus 0.05, accuracy or F1 | 290 calls each, 8-core CPU, no GPU, Chinese and English | per-model scores not given |
| Encoder latency and memory | p50 call latency 0.2 to 3.3 seconds; peak process memory 1.7 to 4.1 GB | | same | range across the three models |
| Dohnuts vs best encoder, write-quality judgment | 0.74 F1 vs 0.17 | | same questions | |
| Dohnuts vs best encoder, memory type classification | 0.70 accuracy vs 0.48 | | same questions | |
| Dohnuts, web relevance, Chinese | 0.94 F1 | chat baseline 1.00 | | closest any local model came to the requirement |
| Jev accuracy on any of these tasks | not stated | | | withheld at the Jev team's request |

## Mechanism details you could implement
- Put every write-path judgment behind one client interface that takes (material, list of typed questions) and returns answers only. Run the current chat model through it first; change the model second. This separates the gain from question shape from the gain from the model.
- Ask all questions about one piece of material in one call.
- Do not ask for reasons when a program consumes the answer.
- Gate extraction with two questions (worth keeping long term; not already saved), compare only against successfully written memories, and treat a timeout or failure as "run the original path".
- Use different acceptance conditions per decision according to what a wrong answer costs: a wrong accept is caught downstream, a wrong reject is lost.
- Keep any rejecting decision in shadow until the chain (what the model saw, which answer was acted on, what was written) can be audited.
- For retrieval, let an inferred time range change ranking and surface it as a suggested filter; enforce only filters the user gave.

## Limitations, caveats, counter-evidence
- No accuracy figure for Jev itself; every quality number is for a chat model or an open-weight model.
- n is 40 per task, one run: "small differences need repeated experiments before we can draw conclusions from them."
- The author states the missing result plainly: "Whether the memories we ultimately save are more accurate, users' full monthly bills are lower, or search is faster still requires production A/B tests covering the complete workflows. We do not have those results yet."
- Candidate review through the decision model did not reduce cost ("Cost did not fall either") and stays in shadow.
- The evaluation sets are the vendor's own, not released. No code.
- Counter-evidence to read alongside: N-20260929-09 (JevBench v1.5) reports open 12B models tying or passing Jev 1.13 on a public leaderboard; here small open-weight models (encoders and a 0.8B LoRA model) fail a product quality bar on memory decisions. The model sizes and tasks differ, so this is a tension, not a direct conflict (inference).

## Takeaways for tuning a memory stack
- Before paying for a System One model at the write gate, rewrite the gate as separate typed questions and batch them with the existing model; in this report that step produced most of the gain.
- A write gate that skips extraction must fail open and must dedup against committed memories only.
- A reject decision needs a stricter acceptance rule than an accept decision.
- Small CPU-only open-weight encoders were not good enough here for bilingual memory decisions; a larger open-weight model is the test still to run.
- In search, a fast decision model can miss the latency budget of a fast path; place it in the deep path or behind a time budget with a fallback reranker.

## Open questions
- What are Jev's precision and recall on the unsaved-knowledge check and on dedup? Not disclosed.
- How much content is actually skipped before extraction in production, and how much skipped content held knowledge worth saving? Not measured.
- Would an open-weight model of 4B to 12B meet the 0.05 requirement in both languages? Not tested.

## Grading and labels
- **Directness: medium.** First-hand measurements in a table, but the System One model's own numbers are withheld.
- **Control: medium.** Same-model ablation of five prompt variants and a predeclared requirement for local models; single run, n of 40.
- **Independence: low.** Vendor evaluating its own pipeline on its own examples; the author thanks the Jev team.
- **Reproducibility: low.** No data, prompts or code released.
- **Applicability: medium.** A memory product's write gate and search, bilingual; personal and work notes, not engineering artifacts.
- **Strength:** builder-report.
- **Pillars:** R9 primary (System One at the write gate and other stages). Secondary R2 (write gate semantics), R4 (when to automate a reject). Memory stage: write_gate. Priority 1; also bears on priority 2.
- **Beliefs:**
  - B11 supports: admission is treated as a separate decision with its own error costs; a wrong reject is unrecoverable, so rejects stay in shadow.
  - B14 supports: the team reports working on "question design and threshold calibration" locally and declines a single confidence threshold.
  - Would create: most of the write-gate saving comes from question decomposition and batching, not the model swap.
  - Would create: open-weight encoder decision models did not meet a chat-model bar on bilingual memory decisions.
- **Contradiction rows:** none against the register. Tension noted with N-20260929-09 above.

## Origin chain
- Posts by @wey_gu and @nowledgelabs quoting @NowledgeMem (link resolves to X article 2105132677699682304) -> blog index https://nowledge-labs.ai/blog -> post "Giving a Memory System Reflexes" -> sections "Separating decisions from generation, with the same model" (ablation table), "Which generation work can we avoid?" (cost model), "Can local models make these decisions?", "What is running today", "Experiment notes" -> this note.
- Independence: same organisation as the product; Dohnuts is by a friend of the author (PsiACE). Shares the vendor (TypeSafe Jev) with most R9 notes on the bus; shares no dataset with them.
