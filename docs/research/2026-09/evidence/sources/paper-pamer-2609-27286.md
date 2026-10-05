---
schema_version: 1
artifact_id: N-20260929-01
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104583094078525629", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.27286
claim_cluster: arxiv:2609.27286
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.27286
source_commit: n/a
strength: paper-ablated
pillar_primary: R3
pillar_secondary: ["R4", "R9"]
memory_stage: assembly
tags: {"mechanism": ["hidden-state-probe", "compression-trigger", "summary-memory", "embedding-retrieval", "step-level-evidence-selection", "majority-vote-heads", "decision-distillation"], "workload": ["long-horizon-agent", "coding-agent", "WorkBuddyBench"], "lifecycle_stage": ["in-session-compaction", "recall"], "cross_cutting": ["token-cost", "single-run", "llm-annotated-labels", "fallback-rules"]}
evidence_grade: {"directness": "high: measures task reward and total tokens of a context-compaction plus summary-recall controller on long agent tasks including 80 code tasks", "control": "medium: same fixed task sets across 15 baselines (Table 4) and 5 backbones (Table 5), component ablation (Table 18); system runs appear single-run with no intervals, and the base agent scores 67.5 in Table 4 vs 68.68 in the separate Table 18 batch", "independence": "low: authors (TierFlow, Renmin, Tsinghua) ran all baselines; WorkBuddyBench is a third-party Tencent benchmark; probe labels come from an unnamed LLM annotator", "reproducibility": "low: no code link found in the PDF; feature extractor is a 'provenance-matched OPD iter-2 Qwen3.5-9B checkpoint' whose availability is not stated; settings in Tables 14 and 15", "applicability": "medium: long coding/security/office/web sessions resemble our engineering agents; the probe needs hidden-state access to a local 9B model; long structured artifacts and cross-session memory not tested"}
beliefs_affected: {"supports": ["B9", "B11"], "contradicts": ["B5"], "would_create": ["A linear probe on a small frozen model's last-token hidden state before the next agent action predicts when in-session context should be compacted (AUROC 0.831) better than length, turn and tool-type metadata (0.751-0.758); keeping only prefix plus the last two complete interaction blocks (26% of tokens) retains most of that signal"]}
claim_correction: The roundup's "pre-action memory control signals" is accurate only in the probing sense: hidden states just before the next action predict compression and recall needs. It is not a check before an agent acts on anything; online, only the compression probe gates behaviour, and recall is plain Top3 embedding retrieval ("The current implementation does not use the learned recall probe as a gate", Section 4.1).
---

# Memory Control Signals Emerge Before Action in Long Horizon Agents (PaMER)

- **URL:** https://arxiv.org/abs/2609.27286
- **Type:** paper
- **Author / org:** Mingxuan Wang, Guorun Yao, Fei Luo, Yinglong Guo, Chao Ning, Bo Wang, Hongyue Chen (TierFlow Team), Yanbiao Ma (Gaoling School of AI, Renmin University; corresponding), Jungong Han (Tsinghua; corresponding). Header "TSINGSHU RESEARCH", TierFlow / TierSense logos.
- **Date:** v1 submitted 23 Sep 2026 (arXiv stamp, cs.AI)
- **Retrieved:** 2026-09-29 (version v1; full PDF read locally at repos/2609.27286.pdf, 35 pages including appendices A to E)
- **Cited by evidence:** https://x.com/RubberDucky_AI/status/2104583094078525629 (@RubberDucky_AI machine-generated roundup; "pre-action memory control signals, WorkBuddyBench")
- **Relevance to a memory stack:** medium-high. A tested in-session compaction policy for long agent runs (prefix + last 2 blocks + Top3 retrieved summaries) with a large token cut at roughly flat reward on a benchmark that includes code tasks, plus 15 context-management baselines on one fixed task set, and a set of fallback rules for memory operations.

## TL;DR
- Probing: on 72,912 decision points from 2,521 trajectories (600 questions, disjoint from the eval benchmark), a linear probe on the final hidden state of frozen Qwen3.5-9B predicts LLM-annotated "compress now" with AUROC 0.831 and "recall needed" with 0.765, vs 0.758 and 0.549 for length + turn + tool-type metadata (Table 1, Table 7; 5 question-grouped splits).
- Prefix + the two most recent complete blocks ("Recent2") uses 26.0% of Full Context tokens and keeps AUROC 0.776 / 0.761 vs 0.829 / 0.780 (Table 2, Table 11).
- PaMER: five distilled MLP heads vote (3 of 5) on the Recent2 state to trigger summarizing older blocks into an external store; later requests retrieve Top3 summaries by cosine similarity. PaMER+ adds step-level raw evidence selection via an LLM router.
- WorkBuddyBench full 260 tasks, DeepSeek-V4-Flash: PaMER 69.4 vs base 69.9 avg reward at 0.72M vs 2.69M tokens/task (-73.2%); PaMER+ 71.6 at 0.76M (-71.7%) (Table 3). Effects vary by domain and backbone: GPT-5.6-Luna loses 2.3 / 2.1 points (Table 5).
- Claim correction: "pre-action" means the hidden state before the next action; the recall probe is analysis only and does not gate retrieval online.

## What it claims / describes

**Probe study (Section 3, Appendix A).** Labels: an LLM annotator (model not stated) marks decision steps where compression or recall is needed; y_t^m = 1[t in A^m(tau)] (Eq. 1). Recall is evaluated only when valid external memory exists. Feature: h_t = last-token output after final RMSNorm of frozen Qwen3.5-9B, d = 4096 (Eq. 2). Readouts: linear sigma(w^T h + b) and a one-hidden-layer MLP (width 256; 4,097 and 1,049,089 parameters per target). Loss: class-weighted BCE with rho = N-/N+ from the training split (Eq. 4). Splits: 70/15/15 grouped by question, seeds 0 to 4; threshold chosen by validation F1. Layerwise: compression AUROC rises with depth (about 0.57 earliest, 0.831 final); recall peaks at block 16 (0.780) vs 0.765 final (Figure 1, Table 9). Last token beats mean pooling at every checkpoint (final: 0.831 vs 0.712 compression; 0.765 vs 0.696 recall).

**Online controller (Section 4, Appendix C, Algorithm 1).**
1. If session id or conversation/tool structure invalid, return raw request.
2. Load persisted memory; if corrupt, discard and start empty.
3. Remove raw blocks already covered by valid stored memories; split into prefix P_t, older blocks O_t, recent R_t (2 complete blocks; a block = one assistant message plus its tool results up to the next assistant message).
4. If Tok(O_t) >= 1,024: extract Qwen3.5-9B final state of P_t + R_t, evaluate 5 heads; u_t = 1 if at least 3 heads exceed their per-seed validation thresholds (Eq. 34). Probe failure: skip compression, recall still allowed.
5. If u_t = 1: summarize older blocks (Qwen3.5-9B, temperature 0, thinking off, max 1,024 output tokens, source budget about 40,000 chars), embed with Qwen3-Embedding-8B (1,024 dims), store M_j = (summary, embedding, identities of covered raw blocks); raw blocks are removed only after storage succeeds and active tokens strictly drop; return P_t + R_t. No recall in the same request.
6. Else if memory exists: query = task + Recent2 (last 30,000 chars), cosine Top3 summaries, insert after prefix and before all retained raw blocks (C = P + E + O + R, Eq. 37).
- Heads are trained on Recent2 with a Full Context teacher: L = WBCE(z, y) + 0.5 BCEWithLogits(z, p_full) (Eq. 9, lambda = 0.5).

**PaMER+ (Section 4.2, Appendix C.3, Algorithm 2).** Each summary records step_details linking to raw steps; an LLM router sees Recent2 and the summary index and outputs summary ids and raw_steps_needed; only complete raw blocks named by the selector are restored. Validation rejects gaps, overlaps, missing, duplicated or unauthorized steps; cache key from sorted summary and step ids; a valid empty selection injects nothing and is not a failure. The authors note the supplied snapshot places this in an LLM-router integration and "its historical system comparisons do not isolate the effect of exact-step selection".

## Numbers

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| compression AUROC, hidden linear | 0.831 | length/turn 0.751; metadata 0.758; hidden MLP 0.827 | Table 1; 72,912 decision points, 5 grouped splits | labels from an LLM annotator |
| recall AUROC, hidden linear | 0.765 | length/turn 0.552; metadata 0.549; MLP 0.763 | Table 1 | |
| compression AUROC with sd | 0.831 +/- 0.036 | Recent2 TF-IDF 0.616 +/- 0.027; Recent2 text embedding 0.546 +/- 0.015 | Table 7, Table 9 | text controls use shorter input; "not a matched-token-budget experiment" (A.4) |
| Recent2 tokens / AUROC C / R | 26.0% / 0.776 / 0.761 | Full Context 100% / 0.829 / 0.780 | Table 2, Table 11 | |
| Selective Raw Top5 | 66.2% / 0.832 / 0.769 | Hidden Bank Recent5 16.8% / 0.769 / 0.730 | Table 2 | lexical selector; offline |
| Qwen Top3 retrieval | 53.9% / 0.804 / 0.764 | Random Top3 47.2% / 0.793 / 0.752; Recency Top3 46.2% / 0.792 / 0.753 | Table 12 | random Top3 is nearly as good (inference from the table) |
| paired sign-flip p, Raw Top5 minus Hidden Bank Recent5, C AUROC | +0.0627, p = 0.0625 | | Table 10, 5 splits | minimum attainable p with 5 splits is 0.0625; "does not establish a two-sided p < 0.05" |
| full benchmark avg reward, DeepSeek-V4-Flash | PaMER 69.4 (-0.4); PaMER+ 71.6 (+1.7) | base 69.9 | Table 3; WorkBuddyBench 260 tasks (80 Code, 50 Office, 60 Security, 70 Web) | no seeds or intervals reported |
| full benchmark Code domain | PaMER 75.3 (-1.7); PaMER+ 76.7 (-0.3) | base 77.0 | Table 3, n=80 | code slightly worse for both |
| tokens per task, full benchmark | PaMER 0.72M (-73.2%); PaMER+ 0.76M (-71.7%) | base 2.69M (698,167,232 total) | Table 3, Appendix D.2 | includes auxiliary memory calls; local feature extraction and embedding compute not in token counts |
| Pilot40 avg / tokens | PaMER 68.0 / 0.90M (-52.4%); PaMER+ 68.9 / 0.98M (-48.1%) | base 67.5 / 1.89M | Table 4, 40 tasks (10 per domain) | |
| Pilot40 best other methods | Periodic Summary n=5 70.2 / 2.37M (+25.5%); Sliding Window K=20 68.7 / 2.02M; CoMem 44.2 / 0.77M; PACE 58.4 / 1.10M; SelfCompact 65.9 / 1.57M; ACON-Core 63.3 / 1.40M; SAM 65.9 / 1.35M; ACM 33.7 / 2.36M | base 67.5 / 1.89M | Table 4 | Periodic Summary n=3 scores 60.5; ACM uses a released policy, not the same acting model |
| cross-model Pilot40 avg delta (PaMER / PaMER+) | GPT-5.6-Luna -2.3 / -2.1; GLM-5.3-Flash +3.1 / -0.3; HY-3 -0.6 / +2.6; MiMo-V2.5 +8.8 / +15.8; Qwen3.8-Flash +0.7 / +6.8 | base agents | Table 5, Table 16 | 40 tasks each |
| cross-model token change | -88.0% / -85.7% (Luna) to -28.0% / -27.6% (Qwen3.8-Flash) | base | Table 17 | |
| component ablation | PaMER reward 0.7000, 0.899M tokens, peak 97.5K | base 0.6868, 3.066M, 280.1K; w/o Recall 0.6370, 0.924M; w/o Compression 0.6887, 3.180M | Table 18, "separate execution batch" | task set for this batch not stated in the table |
| evidence cap, Qwen Top3 | cap 8K mean 5,540 tokens, agreement C 0.818; cap 16K 8,765, 0.843; uncapped 9,167, 0.838 | | Table 13 | offline agreement, not task reward |

## Mechanism details you could implement
- Retain prefix + last 2 complete assistant/tool blocks; compact only when the older portion is >= 1,024 tokens; never split a tool call from its result (Section 4.1).
- Summaries stored with explicit identities of covered raw blocks; remove raw blocks only after summary, embedding and links are stored (Proposition C.3); on any storage failure return the original request.
- Do not recall in the same request that just compacted ("prevents immediate retrieval from undoing the context reduction").
- Insert retrieved summaries after the prefix and before the retained raw blocks; do not insert similarity scores into the prompt; stable identifier order.
- Fallback table (Table 15), verbatim-level: missing session id -> original request; unsafe tool protocol -> no transformation; candidate below 1,024 tokens -> skip compression, recall allowed; probe failure or OOM -> skip compression, record error; summary/embedding/storage failure -> original request, commit nothing; recall transport or shape failure -> original request; invalid step selection or unsafe injection -> reject recall result; valid empty step selection -> inject nothing, not a failure; corrupt state file -> discard, empty store, "do not fabricate prior memories".
- Majority of 5 heads with per-seed thresholds; Proposition C.1 bounds majority error by (1/3) sum of head errors without independence.
- Evidence budget: Top3 capped at 16K recalled tokens kept agreement near uncapped (Table 13).

## Limitations, caveats, counter-evidence
- System evaluations report no seeds, repeats or intervals. The base agent is 67.5 on Pilot40 (Table 4) and 68.68 in the separate ablation batch (Table 18); that run-to-run gap (about 1.2 points, inference) is larger than PaMER's Pilot40 gain (+0.5).
- Probe labels come from "An LLM annotator"; the annotator model is not stated in the pages read. Probe claims are "predictive rather than causal" (Section 2.3, A).
- Recall probe is not used online; the online recall path is plain embedding Top3, and offline Random Top3 is close to learned retrieval (Table 12).
- PaMER+ gains cannot be attributed to exact-step selection: the snapshot includes "additional router, retry, and request-scaffold differences" (Appendix C.3).
- Token accounting excludes local feature extraction and embedding compute (Appendix D.2); billed cost not equal to token reduction.
- Code domain is slightly worse under both variants on the full benchmark (Table 3).
- Cross-backbone results are mixed; GPT-5.6-Luna loses about 2 points.
- In-session compaction within one task; no cross-session or long-term memory, no staleness.
- No code release link found in the PDF; the feature-extractor checkpoint ("provenance-matched OPD iter-2 Qwen3.5-9B") availability not stated.
- The paper's "AI Use Statement" says an LLM was used for literature discovery and as annotator. No instructions aimed at a reader's AI agent found.

## Takeaways for tuning a memory stack
- A cheap, testable default for long engineering sessions: keep prefix + last 2 complete tool blocks, compact older blocks into summaries with provenance links, retrieve Top3 summaries on later turns. On this benchmark it cut tokens 50-73% at roughly flat reward.
- The learned trigger is the expensive part (needs local 9B hidden states); compare it against a fixed token threshold before adopting. Metadata-based triggers reach AUROC 0.758 vs 0.831, and the paper does not report an online arm with a metadata trigger (inference: that arm is missing).
- Copy the failure semantics (Table 15): memory operations must fail closed to the original request, never to a partially rewritten one.
- Recall matters more than compression for reward in their ablation (w/o recall 0.6370 vs 0.7000); compression is what saves tokens.

## Open questions
- Online arm with a fixed token threshold or metadata trigger instead of the probe: not reported.
- Seeds and intervals on system results: not reported.
- Which LLM produced the compression/recall labels and how they were validated: not stated beyond "reviewed by the authors".
- Does it hold on long structured artifacts (design docs, specs) rather than tool traces?

## Grading and labels
- Directness: high. Task reward and total tokens for a compaction plus recall controller on long agent tasks including code.
- Control: medium. Fixed task sets, 15 baselines, 5 backbones, component ablation; no repeats or intervals, batch-to-batch base drift.
- Independence: low. Authors ran all arms; third-party benchmark; LLM-annotated probe labels.
- Reproducibility: low. No code link found; checkpoint availability unknown; settings tabulated.
- Applicability: medium. Coding sessions yes; cross-session memory and structured artifacts no; probe needs local hidden states.
- Strength: paper-ablated.
- Pillars: R3 primary; R4 (learned trigger, thresholds, abstain-to-original), R9 (small frozen model as decision head at a memory stage) secondary.
- Stage: assembly.
- Tags: hidden-state probe, compaction trigger, summary memory with provenance, Top3 recall, fallback rules.
- Beliefs supports: B9 (a stop/compaction rule can cut tokens at near-equal accuracy: -73.2% tokens at -0.4 reward, Table 3; scope is compaction not retrieval stopping); B11 (valid empty selection injects nothing and is distinct from failure, Table 15).
- Beliefs contradicts: B5 (partial, scope-limited).
- Beliefs would_create: hidden-state probe beats metadata for compaction timing; Recent2 keeps most of the signal at 26% tokens.
- Contradiction: B5 ("scheduled summarising consolidation has no published on/off result; nearest measurements are negative"). Table 4 gives in-session on/off results: Periodic Summary n=5 70.2 vs no-summary base 67.5 (+2.6) at +25.5% tokens, but n=3 gives 60.5 (-7.0); PaMER's summarising compaction ablation (Table 18) gives 0.7000 with compression vs 0.6887 without, at 0.899M vs 3.180M tokens. These are single-run, 40-task, in-session results, not persistent-store consolidation, so B5 needs its scope stated (persistent memory) rather than reversal.
- Priority: none matched. The roundup framing suggested priority 3 ("a check before an agent acts"), but the paper has no pre-action check, ontology or trace links.

## Origin chain
- Post: @RubberDucky_AI machine-generated roundup (2104583094078525629) -> arXiv 2609.27286 v1 -> Table 1 (probe), Table 3 (full benchmark), Table 4 (baselines), Table 18 (ablation).
- Independence: authors from TierFlow, Renmin University, Tsinghua. WorkBuddyBench is by the Tencent WorkBuddy Bench Team (arXiv 2607.20911), not the authors. Feature extractor, summarizer and embedder are all Qwen-family; acting models vary. The probe corpus is disjoint from WorkBuddyBench questions (Section 3.1).

## Arm-vs-arm test implied (no card written)
- Arms: A = our current context handling (full history or fixed-threshold truncation); B = Recent2 + summarize-older-blocks-with-provenance + Top3 summary recall, triggered by a fixed token threshold (no probe). Optional C = B with a metadata trigger.
- Dataset: frozen harness, 40 long engineering sessions (coding, review, incident) with graded outcomes, 3 repeats per arm.
- Metric: task pass rate and total tokens per task (including summarizer and embedder calls).
- Margin: B cuts tokens >= 40% with pass rate within 2 pp of A.
- Kill: pass rate drops > 3 pp or recall-dependent tasks fail disproportionately.
- Decision it changes: default in-session context assembly for long engineering agent runs.
- Cost: M (no model training; the probe arm would be L).
