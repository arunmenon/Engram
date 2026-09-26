# Jev-Mem: System-One-Controlled Agentic Memory for Efficient AI Agents

- **URL:** https://arxiv.org/abs/2609.23986 (code: https://github.com/libingzheren/Jev-Mem, per footnote 1)
- **Type:** paper
- **Author / org:** Dongming Jiang, Yi Li, Bingzhe Li (corresponding), Department of Computer Science, The University of Texas at Dallas. Same group as MAGMA (arXiv 2601.03236), HAGE (arXiv 2605.09942) and "Anatomy of agentic memory" (arXiv 2602.19320).
- **Date:** submitted 21 Sep 2026 (arXiv v1), subjects cs.AI, cs.LG
- **Retrieved:** 2026-09-26 (local copy: /Users/arunmenon/MemoryRSI-Signals/evidence/papers/arxiv-2609.23986.pdf, 16 pages read in full including Appendix A and B; abstract page: /Users/arunmenon/MemoryRSI-Signals/evidence/papers/arxiv-2609.23986-abs.html)
- **Cited by evidence:** Decision models as the memory control plane / 2026-09-23 LFrefman; 2026-09-24 runbywren
- **Relevance to a memory stack:** high. It is a complete, thresholded recipe for moving every bounded memory decision (typing, relation linking, consolidation choice, query routing, budget split, candidate scoring, stopping) off the answer LLM onto a typed classifier-style model, with the exact prompts and numeric thresholds in Appendix B.

## TL;DR

- Architecture = three planes: a **System-One control plane** (Jev, TypeSafe AI's typed decision model, called via `TypeSafeClient.system_one`), a **multi-relational memory plane** (canonical nodes + semantic/temporal/causal/entity edge views + shared vector and lexical indexes), and a **System-Two reasoning plane** (the answer LLM, gpt-4o-mini in the reported experiment) that is only called for final answer synthesis and optional merge/promote summarization.
- Every memory control decision is posed as a batch of binary propositions ("Nouls", returning a value in [0, 1]) or a mutually exclusive "Choice" (returns a label plus option distribution), with explicit true/false criteria. Decisions sharing a state are batched in one call: one typing call + one relation call per write; one routing call + at most one stopping call + one scoring call per retrieval round.
- Key thresholds (active profile): relation edge created at score >= 0.60; up to 10 write candidates; consolidation every 20 writes, new representation only if merge/promote prob >= 0.85 and contradiction < 0.85; routing need >= 0.10 activates a graph; expansion budget 80; beam 10; stop when sufficient >= 0.95 and missing < 0.15 and contradiction < 0.15, or continue_useful < 0.15; hard caps depth 8, nodes 60, edges 2400, 16 Jev attempts, 15 s.
- LoCoMo (LLM-as-a-Judge, gpt-4o-mini): overall 0.777 vs 0.700 for MAGMA (+11.0% relative). Build time 158 s vs 1044 s (Nemori, fastest baseline; 6.6x). Query latency 0.93 s vs 1.47 s (MAGMA; -36.7%).
- Evidence is thin: one benchmark only (despite text saying "two"), one answer model, no ablations, no token or dollar cost, no variance, no limitations section, and several text-vs-table mismatches.

## What it claims / describes

### Motivation (Sections 1, 2)
- Formalism: memory M_t; retrieval E_t = R(q_t, M_t) (Eq. 1); answer o_t = L(q_t, E_t) (Eq. 2); update M_{t+1} = U(M_t, q_t, o_t) (Eq. 3).
- Claim: many memory-control operations are "semantic but not generative": they produce bounded outputs (labels, probabilities, scores). Using an autoregressive LLM for them costs token-by-token generation, formatting and parsing on the critical path. Existing systems use either fixed heuristics (efficient, inflexible) or general LLMs (flexible, slow). Jev-Mem positions itself as applying the cascade/routing idea (FrugalGPT, RouteLLM, speculative decoding) at a finer granularity: inside the memory lifecycle rather than per user request.
- Research questions posed: how should System One be integrated across the memory lifecycle; can a weaker reasoner control memory without hurting accuracy; what memory structure and retrieval process best support lightweight control.
- The authors note System-One/System-Two is an analogy for compute allocation, "not as a claim that the underlying mechanisms correspond" (Appendix A.1).

### Data model (Section 3, Eqs. 4 to 6)
- Observation o_t = (x_t, tau_t, mu_t): content, optional timestamp, provenance.
- Memory M_t = (V_t, {E_t^g} for g in G, I_t^vec, I_t^lex), with G = {semantic, temporal, causal, entity}.
- All relation views share the same canonical nodes V_t; multiple typed edges may connect the same pair. Vector and lexical indexes are entry points into the same node space. No duplication of an observation across stores.
- Canonical node stores: original observation, provenance, timestamp, embedding, entities, and type scores.
- Memory objects passed to Jev contain `id`, `content`, `timestamp`, `entities`. The timestamp is observation time, "not necessarily when the event occurred" (Appendix B.1).

### Typed System-One controller (Section 3.1, Appendix B.1)
- Abstraction J(S, Q): S = structured state, Q = batch of explicit decision questions. Output is either independent probabilities per proposition or a distribution over mutually exclusive alternatives.
- API shape (Appendix B.1): a shared `state` object plus a batch of typed `questions` submitted through `TypeSafeClient.system_one`. Each **Noul** specifies a binary proposition with an instruction plus explicit `true` and `false` criteria and returns a value in [0, 1]. Each **Choice** is for mutually exclusive alternatives and returns a selected label and an option distribution.
- Returned values "are not assumed to be calibrated probabilities." Multiple Nouls are independent propositions, not mutually exclusive labels (independence refers to question formulation, not statistical independence).
- Question identifiers are bookkeeping keys, not model input, so every instruction names the state fields it uses. For candidate index i, relation and traversal keys are prefixed `pair_i_` and `candidate_i_`. Questions in a batch do not consume one another's answers.
- Jev model size, architecture, hosting, and per-call latency or price: not stated. Jev is cited only as "TypeSafe AI. 2026. Typesafe ai. https://typesafe.ai/".

### Write path (Section 3.2, Appendix B.2)
Pipeline (Eq. 10): o_t -> type -> candidates -> relations -> M_t.

1. **Admission:** none. The active profile sets `admission_enabled=false`; every valid nonempty observation creates one canonical node. Rationale: avoid an "irreversible learned store-or-discard decision at ingestion time" so information that looks unimportant is not lost before a later query reveals relevance. Selectivity is pushed to structure construction and retrieval.
2. **Typing (Jev call 1, batched):** state = `{"observation": text}`, four Nouls: `episodic`, `semantic`, `procedural`, `preference`. Output t(v) = (t_episodic, t_semantic, t_procedural, t_preference) (Eq. 7), overlapping scores annotating the node, not an exclusive category. Type scores do not decide retention.
3. **Candidate discovery (deterministic, no Jev):** C(v) = TopK_{u in V_t} s_cand(v, u) (Eq. 8), combining vector similarity, lexical overlap, shared entities and temporal proximity; at most K_w candidates (K_w = 10 in the active profile, "at most 10 existing candidate memories"). The exact s_cand combination/weights: not stated.
4. **Relation judgment (Jev call 2, batched over up to K_w pairs):** state contains `new_memory` and a `candidates` list. For every pair (v, u) Jev estimates semantic relatedness, directional causal influence (both directions), same-episode membership, and, only when needed, entity equivalence (alias resolution added only when exact entity identifiers do not already match).
   - Deterministic shortcuts: timestamp ordering directly creates temporal relations; exact shared identifiers directly create entity relations.
   - When temporal order is implicit, the controller chooses among `before, after, during, contains, overlaps, same_time, unknown`.
   - Edge insertion rule: edge of type g inserted only when P(g | v, u) >= theta_rel (Eq. 9); theta_rel = 0.60 ("A returned relation score of at least 0.60 creates the corresponding typed edge").
   - Causal direction: `caused_by` tests candidate -> new memory; `causes` tests the reverse.

### Consolidation and forgetting (Section 3.2, Appendix B.3)
- Periodic maintenance over "a bounded neighborhood" for redundancy, contradiction, obsolescence and useful additional links. Trigger: every 20 successful Jev writes.
- Four Nouls: redundancy, contradiction, obsolescence, link usefulness (their prompt texts are not shown). Then one Choice `representation` with labels `keep_separate`, `merge`, `promote`, `uncertain`.
- It is "a separate post-insertion decision, not an admission filter." Consolidation preserves raw observations; the normal path "records decisions and links; it does not automatically replace source memories."
- Escalation to System Two: a caller-supplied System-Two summarizer creates a new representation only when `merge` or `promote` is selected with probability >= 0.85 and the contradiction score is below 0.85 (as printed; note this is a much looser contradiction bar than the 0.15 used for stopping). The selected-option probability, not a separate confidence summary, controls the threshold.
- Forgetting / deletion policy: not stated. No node is deleted; obsolescence is only assessed and recorded (inference: obsolescence has no described downstream effect on retrieval).
- Neighborhood size for consolidation pairs: not stated.

### Read path (Section 3.3, Appendix B.4, B.5)
Loop (Eq. 26): route -> retrieve -> assess -> expand -> reassess.

1. **Routing (Jev call, one per query):** state contains only `query`. Six Nouls: `semantic`, `temporal`, `causal`, `entity` needs, plus `multi_hop_need` h(q) and `recency_importance` r(q). Output p(q) = {p_g(q)} (Eq. 11). Views are evaluated independently, so several can be active. Active if p_g(q) >= theta_act (Eq. 12); the appendix says graphs with need >= 0.10 get a minimum allocation, i.e. theta_act = 0.10 (inference from B.4 wording).
2. **Budget allocation:** w_g(q) = p_g(q)^gamma / sum over active j of p_j(q)^gamma (Eq. 13); b_g = m + LRound_g[(B - m|A(q)|) w_g(q)] (Eq. 14), with largest-remainder rounding. Active profile: B = 80, m = 1, gamma = 1.0. The budget "does not imply one provider request per edge."
3. **Depth:** D(q) = min{D_max, max(1, ceil(D_max h(q)))} (Eq. 15). Depth hard limit is 8 (so D_max = 8 is the likely value; inference).
4. **Anchor retrieval (deterministic):** reciprocal-rank fusion of vector and keyword rankings, s_RRF(v, q) = sum over L in {L_vec, L_lex} containing v of 1/(kappa + rank_L(v)), kappa = 60 (Eq. 16). Top nodes initialize the visited set and frontier. Number of anchors: not stated.
5. **Evidence check (Jev call, at most one per round):** state = `query`, currently selected top-k `evidence`, retrieval `depth`. Four Nouls: `evidence_sufficient` s_d, `continue_useful` u_d, `missing_evidence` m_d, `contradiction` c_d (Eqs. 17 to 20).
   - Stop when s_d >= theta_suff and m_d < theta_cont and c_d < theta_cont (Eq. 21): 0.95, 0.15, 0.15.
   - Also stop when u_d < theta_cont (Eq. 22): 0.15.
   - Hard caps: depth 8, visited nodes 60, examined edges 2400, Jev attempts 16, retrieval time 15 s. Time budget "is checked between operations and is not a strict preemption guarantee." Caps can terminate retrieval with incomplete evidence.
   - For temporal queries, evidence and candidate objects add `timestamp_role` and `temporal_references` (timestamp identified as observation time, grounded expressions attached with their precision), so sufficiency is judged with the same temporal grounding shown to the answerer.
6. **Expansion + candidate scoring (Jev call, one batched per round):** expand neighbors under per-relation budgets b_g and global limits (nodes, edges, depth, controller calls, latency). Traversal state: `query`, selected `evidence`, proposed `candidates`; each candidate includes memory fields, graph type, relation properties, and source/target identifiers (direction explicit). Four Nouls per candidate: `relevance` a_v, `relation_usefulness` l_v, `new_information` n_v, `supports_current_evidence` c_v.
   - Transition score for candidate reached via graph g (Eq. 23): s(v | q, E_d) = [lambda1 z_v + lambda2 a_v + lambda3 p_g(q) l_v + lambda4 n_v + lambda5 (pi_e + c_v)/2] / sum(lambda_i), where z_v = embedding (cosine) similarity, pi_e = stored edge weight (edge probability). Lambda values: not stated.
   - Recency (Eqs. 24, 25): rho_v = 1 / (1 + max(0, tau_* - tau_v)/day); s~(v) = (s(v) + 0.1 r(q) rho_v) / (1 + 0.1 r(q)). tau_* is not explicitly defined (inference: the query/reference time).
   - Top W = 10 candidates form the next beam and are added to accumulated evidence. "A high relevance score alone is not an unconditional admission to the retrieved evidence."
7. **Answer:** after termination, top-K memories go to System Two: y = SystemTwo(q, E) (Eq. 27). K value: not stated. System Two does no routing, expansion or stopping. Gold answers and benchmark evidence annotations are excluded from Jev states.

### Per-operation call bounds (Section 3.3)
- Write: 1 batched typing request + (if candidates exist) 1 batched relation request over at most K_w pairs.
- Query: 1 routing request + per round at most 1 evidence assessment + 1 batched candidate-scoring request.

## Numbers

### Table 1 (reproduced): LoCoMo, LLM-as-a-Judge, "LLM model is based on gpt-4o-mini"

| Method | Multi-Hop | Temporal | Open-Domain | Single-Hop | Adversarial | Overall |
|---|---|---|---|---|---|---|
| Full Context | 0.468 | 0.562 | 0.486 | 0.630 | 0.205 | 0.481 |
| A-MEM | 0.495 | 0.474 | 0.385 | 0.653 | 0.616 | 0.580 |
| MemoryOS | 0.552 | 0.422 | 0.504 | 0.674 | 0.428 | 0.553 |
| Nemori | 0.569 | 0.649 | 0.485 | 0.764 | 0.325 | 0.590 |
| MAGMA | 0.528 | **0.650** | 0.517 | 0.776 | 0.742 | 0.700 |
| **Jev-Mem** | **0.623** | 0.637 | **0.618** | **0.802** | **0.962** | **0.777** |

### Table 2 (reproduced): efficiency, total memory build time and average query latency (seconds)

| Method | Build Time (s) | Latency (s) |
|---|---|---|
| Full Context | N/A | 1.74 |
| A-MEM | 3636 | 2.26 |
| MemoryOS | 3276 | 32.68 |
| Nemori | 1044 | 2.59 |
| MAGMA | 1404 | 1.47 |
| **Jev-Mem** | **158** | **0.93** |

### Summary of claims

| Metric | Value | Baseline | Setup/benchmark | Caveat |
|---|---|---|---|---|
| Overall LLM-judge | 0.777 | 0.700 (MAGMA) | LoCoMo, gpt-4o-mini | +11.0% relative (0.777/0.700 = 1.110, checks). Single run, no variance |
| Adversarial | 0.962 | 0.742 (MAGMA) | LoCoMo | Largest gain; judge and adversarial handling details not stated |
| Multi-Hop | 0.623 (table) / 0.625 (text) | 0.569 (Nemori) | LoCoMo | Text and table disagree |
| Open-Domain | 0.618 (table) / 0.610 (text) | 0.517 (MAGMA) | LoCoMo | Text and table disagree |
| Single-Hop | 0.802 (table) / 0.797 (text) | 0.776 (MAGMA) | LoCoMo | Text and table disagree |
| Temporal | 0.637 | 0.650 (MAGMA) | LoCoMo | Text says it "matches the best Temporal score of 0.650"; table shows 0.637, below MAGMA and Nemori (0.649) |
| Build time | 158 s | 1044 s (Nemori) | LoCoMo total construction | 84.9% reduction / 6.6x (1044/158 = 6.61, checks). Hardware, concurrency, Jev hosting not stated |
| Query latency | 0.93 s | 1.47 s (MAGMA) | LoCoMo avg per query, retrieval + answer | -36.7% (checks); -46.6% vs Full Context 1.74 s (checks) |
| MemoryOS latency | 32.68 s | n/a | LoCoMo | Cited as example of heavy retrieval-path processing |

- Token counts, dollar cost, Jev call counts per query, and memory size: not stated.
- Ablations (e.g. Jev vs LLM controller, vs heuristics, without routing/stopping/consolidation, threshold sensitivity): none reported.
- "Performs best in five of the six categories": table has five categories plus Overall; Jev-Mem is best on four categories plus Overall (inference from the table).

### Datasets and baselines
- Datasets: Section 4.1 says "two widely used benchmarks" but only LoCoMo (Maharana et al., 2024) is described and reported. LongMemEval, MemBench and MemoryAgentBench are only mentioned in related work. No second dataset result appears anywhere in the paper.
- Baselines (same backbone answer model "whenever applicable"): Full Context; A-MEM (Xu et al., 2025); Nemori (Nan et al., 2025); MemoryOS (Kang et al., 2025a); MAGMA (Jiang et al., 2026a, same authors; the closest structural ancestor with the same four relation views). Mem0, Zep, Letta/MemGPT, LightMem, SimpleMem, Zero-Mem, HippoRAG are discussed but not benchmarked.
- Metrics: LLM-as-a-Judge (Zheng et al., 2023) correctness against reference; total build time; average per-query latency. Judge model and judge prompt: not stated.

## Mechanism details you could implement

Prompts are quoted from Appendix B ("reproduced from the implementation, with candidate index 0 instantiated"; example memories are fictional). Running example: m1 (14 May 2024 10:00) "Mira: My old bicycle broke."; m2 (16 May 2024 10:00) "Mira: I bought a new bicycle yesterday because my old one broke."; query "When did Mira buy a new bicycle, and why?".

**Write: typing Nouls** (state `{"observation": text}`)
- `episodic`: "Does `observation` describe a particular experience or event involving a participant?" true: "A specific past, current or planned event, even if its exact time is unstated." false: "Only a general fact, procedure or preference with no particular event."
- `preference`: "Does `observation` express a participant's preference, aversion or habitual choice?" true: "An attributable like, dislike, preferred option or habitual choice." false: "An isolated action alone, another person's unattributed preference, or no preference evidence."
- `semantic` and `procedural` typing prompts: not shown.

**Write: relation Nouls** (state `new_memory`, `candidates`)
- `semantic`: "Compare `new_memory.content` with `candidates[0].content`. Would a semantic link between these observations help retrieve a shared specific topic or fact?" true: "A specific shared topic, fact or event makes the connection useful." false: "Only generic conversational vocabulary or no meaningful semantic connection."
- `caused_by`: "Compare `new_memory.content` with `candidates[0].content`. Does the candidate event cause, enable or explain the event in `new_memory.content`?" true: "The supplied accounts support this direction of causal influence." false: "Only similarity, chronology, a shared entity, or insufficient causal evidence."
- `causes` (reverse direction), same-episode, entity alias, and implicit-temporal Choice prompts: not shown.
- Threshold: score >= 0.60 creates the typed edge.

**Consolidation Choice `representation`** (every 20 writes)
- Instruction: "Compare `new_memory.content` with `candidates[0].content`. Which representation best fits the relationship between these two observations? Judge from the supplied accounts; do not assume answers to other questions."
- `keep_separate`: "Contradictory accounts, unique details that a combined representation would lose, or distinct facts/events without a supported general pattern."
- `merge`: "Compatible accounts of the same fact or event can be combined without losing unique details."
- `promote`: "Distinct repeated episodes explicitly support a stable general pattern suitable for semantic abstraction; prefer this over merge for repeated events."
- `uncertain`: "Insufficient evidence to choose a safe combined or separate representation."
- Gate to System-Two summarizer: selected merge/promote prob >= 0.85 and contradiction < 0.85. Raw observations kept.

**Read: routing Nouls** (state `query` only)
- `temporal`: "Does answering `query` require event dates, durations, ordering or changes over time?" true: "A time relation is needed to answer correctly." false: "Dates or ordering are incidental to the answer."
- `causal`: "Does answering `query` require explaining a cause, motivation, enabling condition or effect?" true: "Causal or explanatory evidence is needed." false: "Only factual association or chronology is requested."
- `semantic`, `entity`, `multi_hop_need`, `recency_importance` prompts: not shown.

**Read: candidate Nouls** (state `query`, `evidence`, `candidates`)
- `relevance`: "Does `candidates[0].content` contain a fact needed to answer `query`?" true: "Direct answer evidence or a necessary intermediate fact." false: "Only topic overlap or unrelated content."
- `new_information`: "Does `candidates[0].content` add an answer-relevant detail absent from `evidence`?" true: "A distinct relevant detail or missing reasoning link." false: "Only duplicated evidence or irrelevant new details."
- `relation_usefulness`, `supports_current_evidence`: prompts not shown.

**Read: stopping Nouls** (state `query`, top-k `evidence`, `depth`)
- `evidence_sufficient`: "Does `evidence` contain support for every factual part of an answer to `query`?" true: "A grounded answer can be given from these memories without inventing missing facts." false: "Any required fact or reasoning link is unsupported; related topics alone are insufficient."
- `continue_useful`: "Given `query` and `evidence`, is another retrieval round likely to fill a specific gap or resolve a conflict?" true: "An identifiable missing fact or conflict could benefit from more memory retrieval." false: "No identifiable retrieval need remains or more memories are unlikely to help."
- `missing_evidence`, `contradiction`: prompts not shown.

**Active-profile config (collected)**

| Parameter | Value |
|---|---|
| admission_enabled | false |
| K_w (write candidates) | 10 |
| theta_rel (edge creation) | 0.60 |
| consolidation period | every 20 successful Jev writes |
| merge/promote escalation | selected prob >= 0.85 and contradiction < 0.85 |
| theta_act / min-allocation need | 0.10 |
| B (graph-expansion budget) | 80 |
| m (min per active graph) | 1 |
| gamma | 1.0 |
| RRF kappa | 60 |
| beam width W | 10 |
| recency weight | 0.1 r(q) |
| theta_suff | 0.95 |
| theta_cont (missing, contradiction, continue_useful) | 0.15 |
| max depth / nodes / edges / Jev attempts / time | 8 / 60 / 2400 / 16 / 15 s |
| lambda1..lambda5 | not stated |
| final top-K to System Two | not stated |
| embedding model, lexical engine, graph store | not stated |

## Limitations, caveats, counter-evidence

- The paper has no limitations section; everything below is inference unless stated.
- Single benchmark (LoCoMo) despite claiming two; no LongMemEval result, so no evidence on knowledge-update, abstention or multi-session subsets at LongMemEval scale.
- Single answer model (gpt-4o-mini); judge model/prompt not stated.
- No ablations, so it is impossible to attribute the gain to Jev control vs the multi-relational graph (already in MAGMA), no-admission policy, RRF anchors, or stopping. The comparison vs MAGMA (same authors, same four views) is the closest proxy: +0.077 overall, much of it from Adversarial (0.742 -> 0.962).
- No token, dollar, or Jev-call cost accounting; build-time comparison depends on hardware and on whether baselines were parallelized (not stated). Jev is a proprietary hosted model (TypeSafe AI), so the latency figure bundles a network API.
- Internal inconsistencies between text and Table 1 (Multi-Hop 0.625 vs 0.623, Open-Domain 0.610 vs 0.618, Single-Hop 0.797 vs 0.802, Temporal "matches 0.650" vs 0.637, "five of six categories").
- Authors themselves state Jev scores "are not assumed to be calibrated probabilities", yet all control uses hard thresholds (0.60, 0.85, 0.95, 0.15) with no sensitivity analysis.
- No forgetting: memory grows without bound; obsolescence only recorded. Scale behavior beyond LoCoMo-size conversations not tested.
- Consolidation contradiction gate of < 0.85 is permissive (inference: a pair with 0.8 contradiction score could still be merged if merge prob >= 0.85).

## Takeaways for tuning a memory stack

- Phrase each control decision as a binary proposition with explicit true/false criteria and name the state fields in the instruction; batch all questions sharing a state into one call. This bounds control cost to 2 calls per write and 1 + 2 per retrieval round.
- Do not gate admission at write time; keep raw observations and put selectivity into edge creation (>= 0.60) and retrieval scoring.
- Use deterministic signals first (timestamps for temporal order, exact entity IDs for entity links, vector + lexical + entity + time for top-10 candidate discovery); only call the decision model on the residue.
- Replace fixed top-k with a stop rule: sufficient >= 0.95 and missing/contradiction < 0.15, or continue_useful < 0.15, plus hard caps (depth 8, 60 nodes, 2400 edges, 16 controller calls, 15 s).
- Route per query with independent need scores per relation view, split an expansion budget proportionally (B = 80, min 1 per view with need >= 0.10), and scale traversal depth by a multi-hop need score.
- Treat consolidation as a periodic, non-destructive Choice (keep_separate/merge/promote/uncertain) and only spend LLM generation when the choice is confident (>= 0.85).
- Pass timestamp role (observation time vs event time) and grounded temporal references into both the sufficiency check and the answer prompt.

## Open questions

- What are lambda1..lambda5, final K, embedding model, and the missing prompts (semantic/procedural typing, causes, same-episode, alias, entity/semantic/multi-hop/recency routing, relation_usefulness, supports_current_evidence, missing_evidence, contradiction, the four consolidation Nouls)? Presumably in the repo.
- How much of the gain survives with an open small classifier or a small LLM in the Jev slot?
- Results on LongMemEval (the promised second benchmark)?
- How many Jev calls and tokens per query on average, and what is Jev's per-call latency and price?
- Do the thresholds transfer across domains given uncalibrated scores?
- Does obsolescence ever affect retrieval, and how does the store behave over months of accumulation?
- Were the cited evidence numbers checked: yes. LFrefman (0.777, +11.0%, 158 s, 6.6x, 0.93 s, -36.7%) and runbywren (0.777, +11%, 158 s, 6.6x, 0.93 s, -36.7%) match the abstract and Tables 1 and 2 exactly. LFrefman's description (System-One controller over typed, multi-relational memories running routing, budgeting, traversal, scoring, stopping) matches Section 3. Neither post mentions that the result is a single benchmark with no ablations, or that the "fastest competitor" for build time is Nemori while the latency baseline is MAGMA.

---
