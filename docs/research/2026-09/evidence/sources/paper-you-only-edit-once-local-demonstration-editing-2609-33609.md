---
schema_version: 1
artifact_id: N-20260929-34
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104791909348868411", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.33609
claim_cluster: arxiv:2609.33609
feeds: ["decision"]
primary_source: https://arxiv.org/abs/2609.33609
source_commit: n/a
strength: paper-ablated
pillar_primary: R9
pillar_secondary: ["R3", "R5"]
memory_stage: assembly
priority: 1
tags: {"mechanism": ["single-edit-context-refinement", "grpo-verifiable-reward", "frozen-target-as-judge", "small-editor-policy", "keep-delete-replace-actions"], "workload": ["in-context-learning", "text-classification", "few-shot-demos"], "lifecycle_stage": ["assembly", "reranking"], "cross_cutting": ["system-one-model", "transfer-held-out", "cost-latency"]}
evidence_grade: {"directness": "high: numbers read from arXiv HTML v1 tables and figures", "control": "medium: same-model before/after RL, random, keep and larger prompted-editor arms; mean of 5 runs but no standard deviations and a single post-training run", "independence": "low: authors' own evaluation (Tsinghua), code not yet released", "reproducibility": "low: code promised for final version; GRPO hyperparameters only in appendix", "applicability": "low to medium: short classification demos, not long structured artifacts; the one-edit-over-retrieved-set pattern transfers to context assembly"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A small RL-trained editor that makes one Keep/Delete/Replace edit to a retrieved context set, rewarded by a frozen target's correctness, beats keep and a larger prompted editor on classification ICL at about 11 percent extra wall time; untested on retrieval over long structured artifacts"]}
claim_correction: Post numbers match Figure 7; clarifications: training reward uses gold task labels (only edit labels are absent), gains are for classification and turn slightly negative on held-out math (AQuA-RAT 0.8 to 1.9 point declines), and Jev-LDE is a GRPO-tuned Qwen3-1.7B, not a model from the hosted Jev family (naming relation not stated).
---

# You Only Edit Once: Incentivizing In-Context Capability of LLMs via Local Demonstration Refinement (Jev-LDE)

- **URL:** https://arxiv.org/abs/2609.33609 (HTML: https://arxiv.org/html/2609.33609)
- **Type:** paper
- **Author / org:** Jiarong Wen, Qi Wang, Yun Qu, Yixiu Mao, Heming Zou, Haoang Chi, Lizhou Cai, Yiqin Lv, Kaiyu Zhang, Yuhang Jiang, Xiangyang Ji; Department of Automation, Tsinghua University
- **Date:** submitted 2026-09-27 (v1), cs.LG
- **Retrieved:** 2026-09-29, arXiv v1 (abs + HTML). Found via arXiv title search for "You Only Edit Once" after the thread root post gave the title. No local copy.
- **Cited by evidence:** feed decision, priority 1; @AlbertW24045555 thread: https://x.com/AlbertW24045555/status/2104791909348868411 (staged; training and ablation numbers), parent posts 2104791904164651371 (oracle headroom) and 2104791900406632946 (thread root with title). No link in any of the three posts.
- **Relevance to a memory stack:** medium. It is a System One model placed at the assembly stage: a 1.7B policy looks at a retrieved set and makes one Keep / Delete / Replace edit before the target model answers once. Same shape as an admission or swap step over retrieved memory, though tested only on short classification demos.

## TL;DR
- LDE turns demo selection into a one-step local search around the retrieved set. Actions: Keep, Delete(j), Replace(j, z) with z from a pool of 16 Semantic TopK candidates (bge-base-en-v1.5). The editor is Qwen3-1.7B post-trained with GRPO; reward = 1 if the frozen target (Meta-Llama-3-8B-Instruct) answers correctly with the edited demos, 0 otherwise or for invalid output.
- Post numbers verified (Figure 7, 1-shot TREC, Llama-3-8B target): Jev-LDE 65.6%, Llama-3-8B-Instruct prompted as editor 57.8%, Keep 52.8%, Qwen3-1.7B before RL 31.2%, random edit 23.2%.
- Table 1: best or tied-best in "44" of 48 classification configurations; e.g. 1-shot TREC with Qwen2.5-7B target 80.6 vs Semantic TopK 65.4 and best other selector 65.6. Overhead: "11.0% increase in end-to-end wall time over Semantic TopK".
- Transfer without retraining: trained against Llama-3-8B only, it improves 35/36 configurations with Qwen targets, 14/16 on held-out Banking77, and DeepSeek-V4-Flash by +2.2 to +4.4 on TREC-50 and TACRED; math is weaker (held-out AQuA-RAT declines of 0.8 to 1.9 points).
- Headroom: the oracle best single edit (gold labels) adds +26.0 (Llama-3-8B) and +16.8 (Qwen2.5-7B) points on 4-shot TREC; Jev-LDE captures +8.2 and +7.4, so most of the one-edit headroom is still unrealised.

## What it claims / describes
Abstract (verbatim excerpt): "This work simplifies selection by framing it as a constrained local search problem and presents local demonstration editing (LDE). Starting with an initially retrieved set of demonstrations, LDE employs a single structured edit to explore its surrounding neighborhood while balancing performance gains with search costs. ... we train a small LLM, referred to as Jev-LDE. This model as the System-1 modifies the retrieved demonstration set by performing actions such as Keep, Delete, or Replace elements, all within a framework of reinforcement learning with verifiable rewards. At test time, Jev-LDE executes a single edit of the retrieved demonstration set, followed by one inference from the target LLM, avoiding the need for iterative context scoring or subset searches."

**Pipeline.** (1) Retrieve top-k demos Z0 and a pool C of N=16 further candidates by Semantic TopK with normalised bge-base-en-v1.5 embeddings. (2) The editor gets the task instruction, query x, Z0 and the replacement candidates, and outputs one JSON action inside `<answer>` tags (Equation 3): Keep; Delete(j), j in [k]; Replace(j, z), z in the candidate pool. (3) The frozen target answers once with the edited set.

**Training.** GRPO on Qwen3-1.7B. Reward r = 1[y_hat = y] from the frozen Meta-Llama-3-8B-Instruct, 0 for invalid outputs. Advantage normalised within the group: (r - mean) / (std + eps). Training states come from training splits of AGNews, TREC, DBPedia and GSM8K; query counts, learning rate, steps and KL are not in the main text (clipping values in Appendix B).

**Why one edit (thread post 2104791904164651371, matches Figure 2):** "With 16 candidates and 4 shots there are 53 one-edit moves versus 2,380 subsets for a global search."

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| 1-shot TREC acc, Llama-3-8B target | Jev-LDE 65.6 | Llama-3-8B prompted editor 57.8; Keep 52.8; Qwen3-1.7B pre-RL 31.2; random 23.2 | Figure 7; TREC test n=500 | same target used for the training reward |
| 1-shot TREC, Qwen2.5-7B target | 80.6 | Semantic TopK 65.4, BM25 64.6, TopK+ConE 46.6, LMS3 65.6, CASE 65.6, Random 16.8 | Table 1 | Qwen target not used in training |
| 4-shot TREC, Qwen2.5-7B | 87.8 | TopK 80.4, BM25 84.4, CASE 81.8 | Table 1 | |
| 1-shot DBPedia, Qwen2.5-7B | 94.8 | TopK 89.7, LMS3 89.5, CASE 89.7 | Table 1; n=1,000 | |
| 4-shot DBPedia, Qwen2.5-7B | 96.5 | TopK 95.3, BM25 95.4 | Table 1 | |
| 1-shot Banking77, Qwen2.5-7B | 88.4 | TopK 88.6, LMS3 88.7, CASE 88.7 | Table 1; n=3,076; held-out benchmark | below three baselines, one of the non-best settings |
| 4-shot Banking77, Qwen2.5-7B | 92.3 | TopK 91.6, CASE 91.5 | Table 1 | |
| 1-shot TREC, Llama-3-8B | 65.6 | TopK 52.8, TopK+ConE 55.2, LMS3 35.8, CASE 52.6 | Table 1 | |
| 4-shot TREC, Llama-3-8B | 79.6 | TopK 71.4, TopK+ConE 74.0 | Table 1 | |
| best or tied-best | 44 of 48 configurations | six selectors | Table 1 family | our extraction shows only 8 rows |
| improves over Semantic TopK init | 46/48 | | | |
| oracle best single edit, 4-shot TREC | +26.0 (Llama-3-8B), +16.8 (Qwen2.5-7B) | Jev-LDE +8.2, +7.4 | Figure 2 | oracle uses gold labels |
| average 1-shot accuracy | 81.2 -> 88.1 | Semantic TopK | thread root post, "across 3 benchmarks and 4 target LLMs" | as stated in post; not re-derived from tables |
| candidate pool size | N=16: 80.6; N=32: 79.4 | | 1-shot TREC, Qwen2.5-7B; N in {8, 16, 24, 32} tested | larger pool slightly worse |
| wall-time overhead | +11.0% end-to-end | Semantic TopK | | |
| transfer to held-out targets | improves 35/36 configs with Qwen targets; DeepSeek-V4-Flash +2.2 to +4.4 on TREC-50, TACRED | | trained on Llama-3-8B reward only | |
| held-out math | AQuA-RAT declines of 0.8 to 1.9 points | | Appendix G | "less consistent benefits" |
| runs | mean of 5 runs, no standard deviations; "no entry is an average over post-training runs" | | greedy decoding | single trained policy |

## Mechanism details you could implement
- Action space for an assembly-stage editor over retrieved items: `{"action": "keep"} | {"action": "delete", "j": i} | {"action": "replace", "j": i, "z": candidate_id}`, one action per request, emitted as JSON in `<answer>` tags.
- Candidate neighbourhood = top-k in context plus the next 16 by embedding similarity; the paper finds 32 slightly worse than 16.
- Reward = downstream correctness of a frozen target with the edited context, grouped GRPO advantage; no per-edit labels needed, only task labels.
- Baselines worth copying as arms: Keep (no edit), random edit, a larger prompted model as editor, and the same small model before training.

## Limitations, caveats, counter-evidence
- Authors (Appendix G): strongest for classification; math reasoning shows "less consistent benefits"; a single edit cannot fix a badly misaligned initial retrieval; may inherit target-model biases.
- One trained policy, no variance across post-training runs; no standard deviations.
- Code not released ("We will release the complete code of the inference procedure with the post-trained Jev-LDE").
- Demos are short labelled examples; nothing tests long structured artifacts, multi-hop evidence or trace links (inference).
- Name: "Jev-LDE" is described as a Qwen3-1.7B editor; the paper extraction did not explain whether "Jev" relates to the hosted Jev System One model family in our register. Treat as unrelated until stated.

## Takeaways for tuning a memory stack
- An assembly-stage "one edit" step (drop or swap one retrieved item) is a cheap, bounded alternative to full listwise reranking: 53 moves vs 2,380 subsets in their setting, +11% wall time.
- A small policy trained on downstream correctness beat a larger prompted editor (65.6 vs 57.8), consistent in spirit with B13's point that a bigger judge is not automatically better, though the setting differs (inference).
- Include Delete as an allowed action: it is an admission decision, and B11 says admission must be allowed to drop items while a ranker should not default to pruning.

## Open questions
- Does a one-edit step over retrieved memory items (requirements, decisions, tickets) improve an agent's build-time answers? Untested.
- How much of the oracle headroom (+26.0) is reachable with more training or a second edit? Not reported.
- What do GRPO hyperparameters and training query counts look like (Appendix B)? Not extracted.

## Grading and labels
- Directness: high, numbers from arXiv HTML v1.
- Control: medium, within-model before/after RL plus random, keep and larger-editor arms; single trained run, no SDs.
- Independence: low, authors' own evaluation.
- Reproducibility: low, code promised, not released.
- Applicability: low to medium, classification demos only; the edit-over-retrieved-set pattern transfers.
- Pillars: R9 primary (small System One model at a memory stage vs larger prompted model); R3 secondary (context assembly); R5 secondary (RL from outcome reward).
- Stage: assembly (reranking adjacent).
- Tags: mechanism single-edit-context-refinement, grpo-verifiable-reward, frozen-target-as-judge, small-editor-policy, keep-delete-replace-actions; workload in-context-learning, text-classification, few-shot-demos; lifecycle assembly, reranking; cross-cutting system-one-model, transfer-held-out, cost-latency.
- Beliefs: supports none formally; contradicts none; B13 related (small trained editor beats larger prompted editor, different setting); B11 related (Delete is an admission action); would create a lead on one-edit assembly policies.
- Arm-vs-arm test implied: yes, partially: on our workload, arm A = Keep (retrieved set as is), arm B = one Keep/Delete/Replace edit by a prompted small model over a 16-item neighbourhood, scored on build-time answer correctness; an RL-trained arm is unlikely this quarter.

## Origin chain
- @AlbertW24045555 thread: root 2104791900406632946 (title, no link) -> 2104791904164651371 -> staged 2104791909348868411 (feed decision) -> arXiv title search "You Only Edit Once" -> https://arxiv.org/abs/2609.33609 v1 -> https://arxiv.org/html/2609.33609 -> this note.
