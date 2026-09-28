---
schema_version: 1
artifact_id: N-20260927-01
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103828189407834259", "file_id": null, "sha256": null}, {"artifact_id": "post:2103926199978532916", "file_id": null, "sha256": null}, {"artifact_id": "post:2103673542462124217", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.27334
claim_cluster: arxiv:2609.27334
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.27334
source_commit: n/a
strength: paper-ablated
pillar_primary: R3
pillar_secondary: ["R2", "R5"]
tags: {"mechanism": ["read-time curation", "raw trajectory storage", "task-conditioned payload", "GRPO-trained curator", "BM25 retrieval"], "workload": ["ALFWorld", "WebShop", "tau2-bench"], "lifecycle_stage": ["write", "read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: tables compare read-time curation against write-time memory methods on the same executors", "control": "medium: ablations for task conditioning, raw vs distilled storage, filtering and empty retrieval; no matched-token comparison of write-time vs read-time", "independence": "low: single lab (Salesforce AI Research), baselines reimplemented by the authors", "reproducibility": "medium: 3 to 4 runs with different task orderings and std reported; code release not stated in the fetched text", "applicability": "medium: agentic task success with trajectories, not long structured engineering artifacts; payload format hand-designed per benchmark"}
beliefs_affected: {"supports": ["B7", "B16"], "contradicts": [], "would_create": ["Storing raw trajectories and curating per task at read time beats write-time distillation even with an untrained curator (3 benchmarks, 3 executors)"]}
claim_correction: none (the post's +16.2 / +16.3 / +3.9 figures match the paper; the post omits that the tau2 gain is from an untrained GPT-5.4 curator and that no matched-budget comparison exists)
---

# Just-in-Time Memory: Learning to Curate Task-Adaptive Memory for LLM Agents (JitMem, arXiv 2609.27334)

- **URL:** https://arxiv.org/abs/2609.27334 (full text read at https://arxiv.org/html/2609.27334)
- **Type:** paper
- **Author / org:** Yefan Zhou, Yang Li, Zeyu Leo Liu, Semih Yavuz, Shafiq Joty (author list from the arXiv listing post 2103673542462124217; affiliation Salesforce AI Research per the dair_ai post, not stated in the fetched HTML excerpt)
- **Date:** arXiv v1, 23 Sep 2026
- **Retrieved:** 2026-09-27, arXiv HTML v1 (no code commit; code release not stated in the text read)
- **Cited by evidence:** @dair_ai https://x.com/dair_ai/status/2103828189407834259 ; @SciFi https://x.com/SciFi/status/2103673542462124217 ; reply @AliceInfoAi https://x.com/AliceInfoAi/status/2103926199978532916
- **Relevance to a memory stack:** high. This is the paper behind belief B7 ("JITMem") and it now has tables: raw trajectory store + per-task read-time curator beats three write-time memory systems on three executors, with ablations that directly test "distil at write time" against "keep raw".

## TL;DR
- Store raw successful trajectories unchanged; at task time, BM25 over task descriptions retrieves traces and a curator LLM writes a short task-specific "briefing" for a frozen executor. The curator is trained with GRPO on whether that same task succeeds.
- ALFWorld (Qwen3-8B executor): trained JitMem 77.4 SR vs 61.2 for trained SkillOS and 55.7 for ReasoningBank. WebShop: 32.8 vs 16.5. tau2-bench (GPT-5.4 executor, untrained GPT-5.4 curator): 75.6 micro-avg vs 71.7 ReasoningBank.
- An **untrained** curator (JitMem-base) already beats write-time baselines on ALFWorld (60.5 vs 55.7 / 53.1) and uses about half the input tokens of write-time memory (10.9K vs 19.7K to 22.4K per task).
- Ablation: replacing raw storage with ReasoningBank-style distilled summaries costs 1.7 to 8.2 SR; removing the current task from the curator input costs up to 11.4 SR.
- Not tested: matched-budget comparison, long structured artifacts, abstention, or what happens when the bank grows large (authors flag BM25 as a likely bottleneck).

## What it claims / describes
Architecture (Section "method", as read):
1. **Memory bank:** complete, unabstracted raw trajectories. Only trajectories judged successful are stored; success is judged by an LLM-as-judge (the executor model itself; a dedicated judge prompt for tau2-bench).
2. **Retriever:** BM25 over task descriptions only, "kept lightweight, decoupled from trajectory length".
3. **Curator (pi_phi):** reads the current task plus the retrieved raw trajectories and is prompted to "synthesize these raw memories into a concise, actionable briefing". The same trajectory yields different payloads for different queries.
4. **Executor (pi_L):** frozen LLM that receives the payload in context.
5. **Training:** GRPO with the immediate task-success reward (single-step credit assignment, because the payload is used immediately). 100 GRPO steps, batch size 32, group size 8, learning rate 1e-6.
6. **Protocol:** tasks processed in batches that share the memory bank state; the bank is updated after each batch; results averaged over 3 to 4 runs with different task orderings.

Baselines: ReasoningBank (distilled reasoning strategies, cosine retrieval), MemP (multi-granularity memory items), SkillOS (GRPO-trained skill curator with composite rewards), and write-time heuristic memory (verbal reflections, executable skills).

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| ALFWorld SR, Qwen3-8B executor | JitMem trained 77.4 +/- 2.9 | SkillOS trained 61.2 +/- 4.6; ReasoningBank 55.7 +/- 3.1; No Memory 47.9 +/- 1.2 | Table 1, curator Qwen3-8B | 3 to 4 orderings; +16.2 vs strongest baseline |
| ALFWorld SR, Gemini-2.5-Pro executor | 86.2 +/- 1.9 | SkillOS 80.2 +/- 3.1 | Table 1 | +6.0 |
| ALFWorld SR, GPT-5.4 executor | 86.7 +/- 0.7 | ReasoningBank 69.8 +/- 4.0 (SkillOS trained not reported) | Table 1 | +8.8 per paper |
| ALFWorld SR, untrained curator (JitMem-base) | 60.5 +/- 2.6 (Qwen3-8B) | ReasoningBank 55.7, SkillOS-base 53.1 | Table 1 | read-time curation without training |
| WebShop SR, Qwen3-8B executor | 32.8 +/- 1.7 | SkillOS trained 16.5 +/- 0.7; No Memory 9.8 +/- 0.5 | Table 1 | +16.3 |
| WebShop score | 61.1 +/- 0.9 | SkillOS 40.6 +/- 0.7 | Table 1 | continuous metric |
| WebShop SR, untrained curator | 11.7 +/- 0.5 | SkillOS-base 13.6 | Table 1 | untrained JitMem does NOT beat SkillOS-base here |
| tau2-bench micro-avg SR (GPT-5.4 executor) | JitMem-gpt untrained 75.6 +/- 2.3 | ReasoningBank 71.7 +/- 3.9; No Memory 65.0 +/- 2.8 | Table 2 | training-free variants only; Airline 63.5 vs No Memory 65.0 (lower) |
| tau2 Telecom | 72.6 +/- 4.5 | ReasoningBank 61.6 +/- 8.4 | Table 2 | largest gain (+11.0) |
| input tokens per task (ALFWorld, GPT-5.4) | JitMem trained 9.8K; base 10.9K | ReasoningBank 19.7K; SkillOS-base 22.4K; No Memory 9.0K | Table 4 | curator call cost not included in executor tokens (inference) |
| executor steps | 11.6 (trained) | SkillOS-base 16.9; No Memory 17.8 | Table 4 | |
| ablation: distilled instead of raw storage | -1.7 to -8.2 SR | JitMem with raw storage | Figure 2 | "Information irreversibly lost at storage time cannot be recovered." |
| ablation: curator without current task | up to -11.4 SR (ALFWorld), -10.4 (WebShop) | full JitMem | Figure 2 | |
| ablation: store all trajectories with labels vs success-only | -1.5 to -3.4 SR | success-only | Figure 2 | |
| ablation: forced empty retrieval | up to -14.8 SR (ALFWorld), -15.2 (WebShop) | full JitMem | Figure 2 | gains come from retrieved experience |
| executor transfer (curator trained with Qwen3-8B, used with GPT-5.4) | 86.7 +/- 0.7 | trained with GPT-5.4: 88.1 +/- 0.9 | Table 3 | 1.4 point transfer gap |

## Mechanism details you could implement
- Keep the raw episode (full trajectory) as the stored unit; do not summarise at write time. Filter to successful episodes only (their judge is the executor model; see limitations).
- Retrieval key = task description only (BM25). The payload is produced per request by a curator given (new task, retrieved raw traces).
- Curator prompt intent (quoted): "synthesize these raw memories into a concise, actionable briefing". Payload format is hand-designed per benchmark (not published in the part read).
- Training recipe if you want it: GRPO, reward = immediate task success, 100 steps, batch 32, group 8, lr 1e-6. Refreshing the bank after 100 steps and training 50 more gave only +0.9 to +2.8 SR, "not justified by additional cost".
- (inference) For replay (our R1 need), the curated payload must be retained with the episode ids it was built from, because the same raw trace yields different payloads for different tasks.

## Limitations, caveats, counter-evidence
- Authors: "The retriever (BM25) is simple and may become a bottleneck as the memory bank grows large and diverse. The curator adds an extra LLM call per task. The payload format is fixed and hand-designed per benchmark."
- No matched-budget comparison of write-time vs read-time memory; the token table counts executor tokens, not the curator call (inference).
- The success filter uses the executor as judge, so judge and system share a model (R6 concern).
- Untrained JitMem-base is below SkillOS-base on WebShop (11.7 vs 13.6), so "untrained curator matches or beats write-time memory" (post) holds on ALFWorld and tau2 but not WebShop SR.
- tau2 Airline: JitMem-gpt 63.5 is below No Memory 65.0.
- Baselines are the authors' runs; independence low.
- No abstention, knowledge-update or contradiction tests; tasks are episodic agent tasks, not long structured artifacts.

## Takeaways for tuning a memory stack
- Keep raw episodes as the source of truth; treat summaries as disposable, request-time products. This is consistent with B7 and B16 and with the synthesis's "store raw text always".
- If you add a read-time curator, condition it on the current task; the ablation says that is where most of the gain is.
- Budget one extra LLM call per task for curation; expect executor input tokens near the no-memory level rather than doubling.
- Do not store failed trajectories mixed with successes without a filter (1.5 to 3.4 SR penalty here); keep them separately if you want negative evidence (inference).

## Open questions
- Does the gain hold at matched total tokens (curator + executor) against write-time memory?
- How does a BM25-over-task-description retriever behave with thousands of heterogeneous episodes?
- What is the curator's failure mode when retrieved traces are stale or superseded (no supersession semantics in the design)?
- Code, payload templates and seeds: not found in the text read.

## Grading and labels
- Directness high: success-rate tables across 3 benchmarks and 3 executors.
- Control medium: strong ablations, but no matched-budget control and no independent baseline implementations.
- Independence low: one lab.
- Reproducibility medium: variance over 3 to 4 orderings; hyperparameters given; code release not stated.
- Applicability medium: agent tasks with trajectories; not build-time reads over long artifacts.
- Pillars: R3 primary (request-time curation); R2 secondary (what is stored, write-time distillation vs raw); R5 secondary (curator trained on outcomes).
- B7 supports: task-conditioned read-time curation beats write-time distillation on the tasks tested (now with tables and ablation).
- B16 supports: raw trajectories beat distilled memory (ablation -1.7 to -8.2 SR).
- Would create: raw store + read-time curation beats write-time distillation even untrained, on ALFWorld and tau2.
- No contradiction rows.

## Origin chain
post 2103828189407834259 (@dair_ai, via academy.dair.ai summary) and post 2103673542462124217 (@SciFi arXiv bot) -> arXiv 2609.27334 v1 HTML -> Table 1 (ALFWorld, WebShop), Table 2 (tau2-bench), Table 3 (executor transfer), Table 4 (tokens), Figure 2 (ablations), limitations paragraph -> this note. Independence: baselines SkillOS and ReasoningBank are external methods reimplemented in the authors' harness; no shared authors known with other catalogue sources.
