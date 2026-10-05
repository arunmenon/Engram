---
schema_version: 1
artifact_id: N-20260929-22
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104751701345304745", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.32186
claim_cluster: arxiv:2609.32186
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.32186
source_commit: n/a
strength: paper-ablated
pillar_primary: R8
pillar_secondary: ["R2", "R6", "R1"]
memory_stage: safety
tags: {"mechanism": ["memory-poisoning", "inverse-planning-attack", "consolidation", "provenance-bound-authorization", "provenance-rendering", "update-audit"], "workload": ["tool-using-agents", "tau-bench", "toolalpaca", "webshop", "memoryarena"], "lifecycle_stage": ["write", "consolidate", "retrieve", "act"], "cross_cutting": ["security", "authority", "provenance", "red-teaming", "pathway-certification"]}
evidence_grade: {"directness": "high: directly measures low-trust evidence becoming consolidated memory that drives a protected action, on LangMem and Mem0 stacks", "control": "high: matched interventions (restore, hide, delete, fact-only, raw replay), access-matched baseline, paired scenario-cluster bootstrap CIs, blinded audits (kappa 0.77 to 0.95, 0.86)", "independence": "low: authors built the attack, the metric (Path-CASR), the defenses (PBA) and the benchmark; no external replication", "reproducibility": "low: 9-page arXiv PDF; schemas, prompts and full results are in a supplement not in the PDF; authors will release manifests and rubrics but withhold transfer-enabling details; no code", "applicability": "medium: synthetic resettable service/tool fixtures, not engineering agents; mechanism (declarative edit -> consolidated procedure -> protected action) maps onto issue/PR text consolidated into build-time procedural memory (inference)"}
beliefs_affected: {"supports": ["B25", "B24", "B1"], "contradicts": [], "would_create": ["Instruction-shaped injection gates do not cover declarative low-trust edits that consolidation turns into action-guiding procedures; in BMA, provenance rendering left 11.0% Path-CASR while dispatch-time provenance-bound authorization cut it to 2.0% at 92.1% legitimate-action success (one paper, synthetic fixtures)"]}
claim_correction: none
---

# BMA: Backchain Memory Attacks Create Unauthorized Control Paths in LLM Agents

- **URL:** https://arxiv.org/abs/2609.32186
- **Type:** paper (cs.CR)
- **Author / org:** Kaisheng Fan, Yishu Gao, Weizhe Zhang (Harbin Institute of Technology; Zhang also Peng Cheng Laboratory), Xunzhu Tang, Tegawende F. Bissyande (SnT, University of Luxembourg)
- **Date:** 2026-09-26 (v1)
- **Retrieved:** 2026-09-29, arXiv v1 (abstract page and PDF; HTML version returned 404). Supplementary material referenced throughout ("Full results appear in the supplement") was not in the PDF and was not read.
- **Cited by evidence:** X post 2104751701345304745 by @gastronomy (arXiv RSS bot), https://x.com/gastronomy/status/2104751701345304745, via short link https://ift.tt/1S3A2Qj which resolves (curl -sI location) to https://arxiv.org/abs/2609.32186v1
- **Relevance to a memory stack:** high. It attacks the consolidation step itself: the adversary never writes memory, the agent's own memory pipeline turns one edited low-trust record into a persistent procedure that later drives a protected action. It also measures three memory-side defenses and one dispatch-time defense.

## TL;DR
- Threat: an external contributor makes "one bounded, declarative edit" (at most 96 tokens) to a low-trust, source-owned span. The agent's memory governor consolidates it into persistent memory; a later clean task retrieves it and the agent performs a protected action the source cannot authorize (Figure 1: "cancel first; verify identity afterward"). The adversary never writes memory, never alters the task and gets no feedback at execution time.
- Headline (abstract, Table 3): across 400 scenarios (240 sealed test), 4 substrates, 3 decision backbones, BMA reaches "18.8% Macro Path-CASR, compared with 13.4% for the strongest access-matched baseline" (difference 5.4 points, 95% CI 2.0 to 8.8). Plain ASR is higher for the baseline (36.5% vs 31.2%); only "60.3% of BMA's behavioral hits pass all registered pathway and intervention checks versus 36.7% for the baseline".
- Defenses (Table 6): update validation (UpdateAudit) 13.7% Path-CASR, provenance rendering (ProvenanceAware) 11.0%, full provenance-bound authorization (PBA) at dispatch 2.0% with 92.1% legitimate-action success (vs 95.9% undefended). Under a PBA-aware adaptive attacker residual Path-CASR is 3.7% (Table 7).
- Memory systems: a LangGraph-LangMem stack (primary) and a native Mem0 stack. Not A-Mem, not Letta/MemGPT. On Mem0, frozen LangMem edits yield 9.2% vs 7.9% A-Path; with Mem0-native preparation 14.9% vs 11.5%.
- Claim check: the post is an RSS bot relaying title and abstract; numbers in the abstract match Tables 3, 4, 6. No claim correction.

## What it claims / describes

**Setting (Problem Setup, Eq. 1 to 3).** Each scenario has immutable history H, one editable contribution e from source s, a target behavior C*, and an edit contract d. An authority contract Pi = (Permit, Critical, Endorse) says whether the source or a trusted endorsement authorizes an action; an action is "authority-eligible" (E=1) when it is critical and has neither basis. Memory pipeline: governor G ingests the edited history once, M = G(M0, H + e); retriever R returns r = R(M, x) per clean task x; backbone D produces behavior Y = D(x, r). The evaluator registers per scenario a target memory specification h-bar = (target condition, action relation, scope, memory role, retrieval cue) before attack preparation.

**Threat boundary (verbatim, Problem Setup).** "The external contributor may submit one bounded declarative edit to a source-owned span. It receives no memory, retrieval, trajectory, reset, or deployment feedback and cannot alter the agent, persistent state, or sealed tasks." Preparation uses "an authorized red-team evaluator with a resettable staging instance and a known target rule". Grey-box: "Model weights, logits, activations, and hidden states remain inaccessible." Edits may replace "one contiguous source-owned span of at most 96 tokens, without changing immutable history, source identity, tool output, protected fields, trusted approval, or policy events" (Experimental Setup).

**Metrics (Eq. 4, Table 1).** Matched interventions: GEN (expose generated memory), REF (restore unedited source), ABS (hide contribution-rooted memory), FACT (retain a sourced, qualified fact record), RAW (replay edited episode without generated guidance), DEL (delete contribution-rooted memory and descendants).
- ASR: any target behavior after editing.
- DM-ASR: behavior must disappear under REF, ABS, RAW and DEL (memory-mediated).
- Path-CASR (primary): DM-ASR plus the descendant "must satisfy the registered specification h-bar, enter the decision context, and also fail a source-bounded fact control" (FACT must be behavior-negative).
- ACMR / A-Path: DM-ASR / Path-CASR restricted to authority-eligible branches.
- Utility Loss in points.

**Attack (Backchain Memory Attack section, Figure 2).** Two phases.
1. Pathway-first candidate c = (h, z, a): h = target memory (applicability, action relation, scope, memory role, retrieval cue), z = transformation hypothesis (what consolidation keeps, weakens, abstracts), a = the bounded edit. "The three objects therefore state, respectively, what memory is needed, how the source might produce it, and what text to change." A candidate gate rejects duplicates (canonical signature over (h, z)) and invalid edits (location, length, source-bounded gate, coherence a -> z -> h).
2. Preparation: on resettable development scenarios observe formation m = MemSat(M, h), routing u = RouteSat(r, h), behavior b (Eq. 6). First-failed-link frontier (Table 2): NoMem (m=0) -> revise z; NotRouted (m=1, u=0) -> revise kappa, sigma, tau; NoEffect (m=u=1, b=0) -> revise rho, alpha; Hit -> retain, stop. Outcomes stored in an experience bank. At most B_dev rounds; at most eight resettable executions per scenario.
3. Execution (held-out): retrieve de-identified experience, generate K=16 pathway-distinct candidates, a frozen critic scores formation, routing, behavior in {0,1,2}, rank by (min link score, sum of link scores, minus edit length) (Eq. 7), commit the top edit once, no feedback; abstain if no valid candidate.

**Setup (Experimental Setup).** 400 balanced scenarios from tau-bench service tasks, ToolAlpaca-derived tool use, modified WebShop, and MemoryArena-derived multi-session tasks; splits 120 development / 40 validation / 240 sealed test. Each test scenario has ten clean tasks and three frozen backbones, "yielding 7,200 task-backbone branches while retaining the scenario as the independent statistical unit". Specifications reviewed by two annotators without access to attacks (kappa = 0.77 to 0.95); pre-attack adjudication revised 45 of 400 specifications. Primary stack: "LangGraph-LangMem stack uses Qwen3.5-4B as memory writer, BM25 and BGE-M3 reciprocal-rank fusion with k = 4, and Qwen3.6-27B, Llama-3.1-70B-Instruct, and DeepSeek-V4-Pro as decision backbones". Attacker: Qwen3.5-9B proposes, repairs, ranks. Transfer: four held-out consolidation configurations, a 27B replacement writer, native Mem0. Baselines: DirectGen, evidence-only OEP-1, GEPA-Edit, BMA-Zero (empty bank), Trace-Repair (strongest access-matched: same feedback, budgets, one-shot protocol, but repairs act on free-text target directly). Frozen authority audit: 216 eligible test scenarios. CIs: scenario-cluster paired bootstrap.

**Defenses (Memory-Side Controls and Dispatch Enforcement).** UpdateAudit (update validation), ProvenanceAware (provenance rendering in context), PBA: "propagates source trust through derived records and blocks a registered critical action unless a trusted endorsement or standing policy matches its entity, time, tool, action, and argument scope; memory remains available for reasoning." PBA "requires origin-preserving derivations, scoped endorsements, and a critical-action registry".

## Numbers

| metric | value | baseline | setup/benchmark (n) | caveat |
|---|---|---|---|---|
| ASR (Table 3) | BMA-Exp 31.2 | DirectGen 27.5, OEP-1 31.8, GEPA-Edit 34.3, Trace-Repair 36.5, BMA-Zero 22.0 | 240 sealed scenarios x 10 tasks x 3 backbones = 7,200 branches | BMA is not best on raw ASR |
| DM-ASR / ACMR (Table 3) | 22.7 / 21.5 | DirectGen 11.9/11.3, OEP-1 15.5/14.8, GEPA 15.2/14.4, Trace-Repair 18.0/17.0, BMA-Zero 14.0/13.3 | same | ACMR restricted to authority-eligible branches |
| Macro Path-CASR / A-Path (Table 3) | 18.8 / 17.9 | DirectGen 8.2/7.5, OEP-1 11.1/10.2, GEPA 10.9/9.9, Trace-Repair 13.4/12.6, BMA-Zero 10.5/10.0 | same | primary endpoint |
| Utility Loss, points (Table 3) | 2.7 | DirectGen 1.3, OEP-1 2.6, GEPA 1.9, Trace-Repair 3.8, BMA-Zero 0.5 | same | |
| Path-CASR difference vs Trace-Repair | 5.4 points, 95% CI 2.0 to 8.8 | | scenario-cluster paired bootstrap | |
| Share of behavioral hits passing full pathway | 60.3% | 36.7% Trace-Repair | Figure 3 (ASR -> complete path -> Path-CASR: BMA 31.2 -> 27.5 -> 18.8; Trace 36.5 -> 20.5 -> 13.4) | |
| Path-CASR hits on authority-eligible branches | 95.3% | | | |
| Cells / scenarios led | higher point estimate in all twelve backbone-substrate cells; leads on 151 of 240 | | | |
| Formation / conditional routing gain | +7.5 / +7.6 points; behavioral influence differs 2.4 points | | Figure 4 (IR, RR, AUR) | distinct conditional denominators |
| ACMR removed by source-bounded fact intervention | 19.4 of 21.5 points | | blinded fidelity audit passes 93.8% of controls (kappa = 0.86) | |
| Validity checks (Figure 5), BMA vs Trace | oracle diagnostic 18.8 vs 14.8; layout-matched sham 18.1 vs 12.9; source-valid recoding 17.6 vs 12.2 (A-Path); observation-preserving 15.7 vs 11.4 (A-Path); Mem0-native 14.9 vs 11.5 (A-Path) | | "all five paired 95% confidence intervals ... exclude zero" | |
| Held-out consolidation policies, Path-CASR (Table 4) | episode-preserving 12.8, scope-preserving 14.5, atomic typed 15.4, type-aware minimal 15.9; held-out mean 14.7 | primary reflective 18.8 (retention 100.0) | frozen edits | retention 68.1, 77.2, 82.1, 84.6; mean 78.0 |
| 27B replacement writer | 11.4% Path-CASR | 9.6% Trace-Repair | paired advantage 1.8 (95% CI 0.1 to 3.5) | |
| Mem0, frozen LangMem edits | 9.2% A-Path | 7.9% | | |
| Mem0, native preparation | 14.9% | 11.5% | paired gain 3.4 (95% CI 0.6 to 6.2) | |
| Conservative measurement (Figure 6), paired gap | registered 5.4; fact-control adverse 4.9; audit-calibrated 4.3; maximal adverse 3.8 (95% CI 0.3 to 7.2) | | | |
| Human audit precision/recall | formation 96.0/93.5, routing 97.3/95.0, behavior 98.0/97.0, lineage/deletion 98.2/96.0 | | | |
| Ablations, Path-CASR (Table 5) | BMA-Exp 18.8 | PostHoc 12.3 (-6.5 [-9.5, -3.5]); Binary 15.1 (-3.7 [-6.4, -1.1]); BMA-Zero 10.5 (-8.3 [-11.3, -5.3]); NoCritic 15.7 (-3.1 [-5.7, -0.5]) | Dev./Hit: 7.8, 11.0, 10.6, 13.4, 7.8 | |
| Field unlocking | upstream regression 16.3% -> 27.7%; Dev./Hit 7.8 -> 10.9 | | | |
| K 16 -> 32 | +0.8 Path-CASR; context 26K -> 47K tokens | | | |
| Retrieval variants | Path-CASR retains 86.2 to 93.6% | | | |
| Attack cost | 7.8 target executions per Hit vs 9.7 Trace-Repair (19.6% fewer); +9.3% serialized latency (11.8 s vs 10.8 s); attack tokens 20.5K -> 26.0K | | | |
| Defenses (Table 6): Disp./ASR, Path, Fact/Legit. | No defense 64.4/31.2, 18.8, 100.0/95.9; UpdateAudit 53.0/25.0, 13.7, 92.2/86.4; ProvenanceAware 44.3/21.6, 11.0, 97.3/90.9; Full PBA 10.9/5.1, 2.0, 97.3/92.1 | No defense | frozen BMA-Exp, 7,200 branches for Path | Fact = benign fact retention, Legit. = legitimate-action success |
| PBA latency | +5.1% | | | |
| PBA-aware stress (Table 7): ASR, ACMR, Path, Legit. | Frozen BMA-Exp 5.1, 2.7, 2.0, 92.1; PBA-aware Trace 7.4, 4.0, 2.9, 91.8; PBA-aware BMA 8.6, 4.8, 3.7, 91.4 | | "matched bounded preparation" | |
| Seeds / intervals | scenario-cluster bootstrap CIs; "Path-CASR remains stable across proposal seeds" | | | number of seeds not stated in main text |

## Mechanism details you could implement
- **Pathway certification as a red-team metric.** Count a poisoning success only if the behavior disappears when the source edit is restored (REF), generated memory is hidden (ABS) or deleted with descendants (DEL), the raw episode is replayed without generated guidance (RAW), and a sourced, qualified fact record alone (FACT) does not produce it. This separates memory-mediated control from coincidence. Directly reusable for our R8 tests.
- **First-failed-link diagnosis** (formation -> routing -> behavior) is a debugging frame for any memory pipeline failure, not only attacks: did the memory form, was it retrieved into context, did it change the decision.
- **Provenance-bound authorization (PBA).** Components named in the paper: origin-preserving derivations (derived/consolidated records carry source trust), a critical-action registry, scoped endorsements matched on "entity, time, tool, action, and argument scope". Memory is still served for reasoning; enforcement happens at dispatch. Measured cost: legit success 95.9 -> 92.1, benign fact retention 100.0 -> 97.3, +5.1% latency.
- **What did not suffice:** rendering provenance in context (11.0%) and validating updates at write time (13.7%, with legit success dropping to 86.4).
- Retrieval config used as the target system: BM25 + BGE-M3 with RRF, "k = 4"; memory writer Qwen3.5-4B in LangMem.

## Limitations, caveats, counter-evidence
- Synthetic, resettable fixtures: "Experiments use resettable synthetic fixtures without real accounts or irreversible actions." Workloads are service/tool/shopping tasks, not software engineering.
- Absolute rates are modest (18.8% Path-CASR best attack); the preparation phase assumes an authorized red-team evaluator with a staging instance and known target rule, which is a strong assumption for a real external attacker (inference).
- Only LangMem and Mem0 tested. A-Mem, Letta/MemGPT, Zep and graph memories are not evaluated.
- Defense evaluation uses the authors' own PBA design; the PBA-aware adaptive attack uses "bounded defense-aware preparation", so a stronger adaptive attacker is not ruled out.
- Full schemas, prompts, pseudocode, intervention rules and per-cell results are in a supplement not in the arXiv PDF; I did not read it. Code not released; authors "will release manifests, rubrics, and de-identified outcomes while withholding transfer-enabling details".
- Single author group built attack, metric, benchmark and defense; no independent replication.
- The edit is declarative (a "local exception" report), not an instruction. An instruction-detecting injection gate (as in B24's jevmem gate) would likely not flag it (inference; not tested in the paper).
- No instruction-bearing content aimed at AI agents was found in the source.

## Takeaways for tuning a memory stack
- Treat consolidation as a trust boundary: derived or summarised memories must inherit the lowest trust of their inputs (origin-preserving derivation). A procedure generalised from one low-trust report is still low-trust.
- Do not rely on write-time injection detection or on showing provenance to the model. Enforce authority at action dispatch: a critical-action registry (for us: merge, deploy, delete branch, change spec status, run migrations; inference) that requires a trusted endorsement independent of memory content.
- For engineering agents, the analogue path is: issue comment / PR description / CI log (low trust) -> consolidated "project procedure" memory -> build-time read -> protected action (inference).
- Adopt Path-CASR-style interventions (REF, ABS, DEL, RAW, FACT) in our R8 test harness so that a detected "poisoning success" is attributable to memory.
- Budget: PBA cost roughly 4 points of legitimate-action success in this setup; measure that on our workload before adopting.

## Open questions
- Does BMA transfer to graph memories with typed supersede edges or to append-only ledgers where consolidation is not summarising?
- What rate would a B24-style instruction gate achieve against these declarative edits? Not tested.
- How often do real low-trust sources in an engineering workflow get consolidated into procedural memory at all? Our consolidation is default off (B5); does BMA need summarising consolidation, or does plain extraction suffice? Table 4 shows 12.8 to 15.9 across four consolidation policies, all non-zero.
- Proposal seed count and per-backbone breakdown are in the unread supplement.

## Grading and labels
- **Directness:** high. Measures exactly the low-trust -> consolidated memory -> protected action path.
- **Control:** high. Matched interventions, access-matched baseline, pre-registered specs, blinded audits, paired cluster bootstrap.
- **Independence:** low. Same authors for attack, metric, benchmark and defense.
- **Reproducibility:** low. No code; supplement not in PDF; transfer-enabling details withheld.
- **Applicability:** medium. Synthetic service/tool fixtures; mechanism plausibly maps to engineering agents (inference).
- **Pillars:** R8 primary (poisoned evidence, execution authority); R2 secondary (consolidation turns evidence into procedure); R6 (Path-CASR as an evaluation-integrity device); R1 (provenance through derived records).
- **Stage:** safety.
- **Tags:** mechanism memory-poisoning, inverse-planning-attack, consolidation, provenance-bound-authorization; workload tau-bench, ToolAlpaca, WebShop, MemoryArena; lifecycle write, consolidate, retrieve, act; cross-cutting security, authority, provenance.
- **B25 supports:** dispatch-time authority enforcement (PBA) is the strongest measured control, 18.8 -> 2.0; conclusion: "consolidation may transform evidence for reasoning, but it must not transform evidence into permission."
- **B24 supports (first clause only):** extracted and consolidated memories behave as untrusted input; the paper does not test an injection gate, and its declarative edits suggest instruction gates are insufficient alone (inference).
- **B1 supports (indirect):** PBA requires origin-preserving derivations, i.e. source identity carried through consolidation.
- **B18:** not directly tested (BMA is adversarial, B18 is about unintended outcome learning); memory-mediated bypass of a verification gate is shown, but with intent.
- **Would create:** instruction gates do not cover declarative edits turned into procedures by consolidation; dispatch-time provenance-bound authorization measured 2.0% vs 11.0% provenance rendering (grade: lead).
- No contradiction with any belief.

## Origin chain
@gastronomy post 2104751701345304745 (automated arXiv RSS relay, no commentary) -> https://ift.tt/1S3A2Qj -> https://arxiv.org/abs/2609.32186v1 -> PDF: abstract, Problem Setup (threat boundary), Tables 1 to 7, Figures 3 to 6, Scope and Ethics. The post adds no independent evidence; all numbers come from the authors' own evaluation.
