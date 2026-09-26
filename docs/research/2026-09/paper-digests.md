# Paper digests — September 2026 restart

One entry per paper or article received during the restart. Each entry states what the work does, the mechanism it introduces, what it implies for Engram, and a verdict: **adopt** (a concrete change to make), **adapt** (a pattern to reinterpret for Engram), or **context** (informs positioning; no code change). Entries are appended as papers arrive; the [README](README.md) carries the running "path forward".

Access note: arxiv.org, huggingface.co and most paper mirrors are blocked from this environment. Where the full text was supplied as a PDF it was read in full and the entry says so; otherwise the digest uses the abstract, search-engine excerpts and the paper's GitHub repository.

---

## D1. An RSI Taxonomy — Yaowei Zheng (LlamaFactory), Sep 2026

**Received as:** screenshots of the article (X post), 2026-09-25. Draws on the *Awesome RSI* repository.

**What it says.** Defines recursive self-improvement as `A(t+1) = U(A(t), τ(t), f(t))`: after a task, the agent uses its trajectory τ and feedback f to modify its own state through an update mechanism U. Agent = Model + Harness; Harness = context, memory, skills, tools, harness code. Dimensions: what evolves (parameters / context / memory / skills / harness code); how versions evolve (chain / tree / graph); who updates (self / teacher / joint); when (offline / online / hybrid); plus acceptance criteria, feedback source and type, update frequency, experience scope. §2.2 distinguishes *context* (visible to the model now) from *memory* (stored externally, becomes context only when retrieved), with Prime Agent as the representative context-evolution system. §2.3 defines memory evolution as selecting valuable experience from logs, turning it into reusable lessons and revising old memories on new evidence, with ReasoningBank as the representative system: retrieve strategies → act → LLM-as-judge decides success → extract items from **both** successful and failed trajectories → consolidate; MaTTS scales attempts to get contrastive signal; +3.7–6.2 pp WebArena, +3.4–4.0 pp SWE-bench Verified.

**Implication for Engram.** Engram is the *substrate* an update mechanism writes into — the trajectory store (ledger), the memory and skill store (graph), and the memory→context boundary (read path) — not an RSI system itself. Its version structure is a *graph* (DERIVED_FROM/SUPERSEDES) and replayable, which no system in the taxonomy's table can claim. What it lacks is exactly the taxonomy's other axes: an explicit U with acceptance criteria, an outcome feedback signal f, and a running skills layer. Full treatment: [rsi-positioning.md](rsi-positioning.md).

**Verdict:** **adapt** — adopt the taxonomy as Engram's framing; implement T1–T3 from the RSI doc (explicit gated update operator, outcome feedback via retrieval receipts, procedural memory with success statistics and a negative-evidence node).

---

## D2. Mendel Gödel Machine: Recursive Self-Improving Coding Agents via Comparative Evolution — Changzhi Liu, Yilun Liu, Sikuan Yan, Volker Tresp, Yunpu Ma (UESTC / LMU Munich / MCML); arXiv 2608.07645, 7 Aug 2026

**Received as:** full PDF (56 pages), 2026-09-25; read in full. Code: [RealLcz/MGM](https://github.com/RealLcz/MGM).

### What it does

MGM sits in the Darwin Gödel Machine → Huxley Gödel Machine line: an archive (tree) of coding-agent variants, each a *genotype* (its scaffold source code) with a *phenotype* (its outcomes on evaluated tasks). HGM already chose *which* node to evaluate or expand by Thompson sampling over Beta posteriors on node- and clade-level success/failure counts. MGM's claim is that the *self-modification step itself* was under-designed: every prior system edits an agent from **one failure trajectory on one task**, and uses the growing archive only as a leaderboard. MGM splits the expansion operator into three, chosen by which evidence the archive can supply:

| Operator | Evidence E | Eligible when | What the editor is asked |
|---|---|---|---|
| **Clonal mutation** Φ_CM (= HGM/DGM) | one failed trajectory of the node | node has ≥1 failed task | diagnose the failure, edit to avoid similar failures |
| **Reaction-norm mutation** Φ_RM | ≥2 trajectories of the *same* node on *different* tasks, at least one failed | node evaluated on ≥ m_RM tasks | find the recurring or contrastive behavioural pattern across the trajectories; implement a *general* improvement |
| **Cross-lineage hybridization** Φ_CH | trajectories of *two different* nodes on the *same* task, not solved by both | overlap exists | the failing agent extracts a transferable behavioural trait from the reference trajectory and adapts it to its own code — **no source is spliced** |

Two supporting mechanisms:

- **A failed-task pool.** Tasks that exposed a failure in *any* lineage get a sampling boost β_fail when choosing the next evaluation task for any agent. This costs no extra evaluations; it deliberately creates task overlap across lineages so that Φ_CH comparisons become available, and concentrates evaluation where it is diagnostic.
- **Operator sampling** among eligible operators with weights λ (repo default CM:RM:CH = 0.1:0.45:0.45). If none is eligible, the step is spent on another evaluation instead.

**Acceptance / selection.** There is no per-child gate: a child always joins the tree (attached to the *failing* lineage for Φ_CH, or to the higher-utility lineage when both failed). Quality is enforced statistically — Thompson sampling over outcome posteriors decides which nodes get further evaluations and expansions, and the "best-belief" node is reported at the end. Contrast Recuris (landscape §7), which gates each localised patch explicitly.

**Theory.** Under an additive fitness model (genotype = binary vector of L loci; task succeeds iff its k required loci are all correct; the editor sees only phenotypes), comparative evidence *compresses the candidate defect set*: Φ_RM to the intersection of the two tasks' loci, Φ_CH by filtering out loci the reference agent proves non-causal. Hence strictly higher effective fix probability than Φ_CM (Prop. 1). Monte Carlo confirms; with ratio ρ = 1 (no diagnostic advantage) MGM collapses to HGM.

### Results (Qwen3.6-35B-A3B backbone, 200 evaluations + 24 expansions, 60-task subsets)

| | Initial | HGM | MGM |
|---|---|---|---|
| SWE-bench Verified-60 | 68.3 | 73.3 | **78.3** |
| Polyglot-60 | 50.8 | 77.9 | **93.2** |
| Ablation, Polyglot-60 | | w/o Φ_RM 79.7 | w/o Φ_CH 74.6 |

Same budget, comparable token cost per operator, comparable wall-clock. Full Polyglot-225: 93.3 %; transferring the Qwen-evolved scaffold to DeepSeek-V4-Pro: 96.9 %. Cross-benchmark (evolved on Polyglot, frozen, evaluated on SWE-bench Pro / Multilingual): HGM −3.4 / +1.6 pp, MGM **+10.0 / +13.3 pp**. Cross-model (scaffold evolved on Qwen, run on DeepSeek-V4-Flash/Pro): MGM +16.7 / +30.0 pp vs initial. Φ_CH is the more important operator.

**Two findings beyond the headline.**
1. *Diagnosis ability beats coding ability.* A larger, coding-specialised backbone (Qwen3-Coder-Next-80B) produced far weaker self-improvement (33.3 → 41.7) than the smaller general-reasoning model (68.3 → 78.3), because the step that matters is inferring *why* the scaffold failed from trajectories, not writing the patch (App. F.2).
2. *What was actually learned is a workflow.* The evolved skills cluster tightly around one procedure: read tests and stubs as a strict contract → extract a structured `contract_plan` (signatures, constructors, verbatim error messages) → implement against it → checklist self-audit → test-driven repair loop (App. F.3, H.1). On SWE-bench the evolved agent added **provenance tracking of which files it viewed** and a **diff-minimality filter** that drops patch hunks unrelated to the files it inspected (App. H.2). HGM's changes were more dispersed and less consolidated.

**Limitations (authors').** History-dependent: with a small archive or sparse overlap there is no comparative evidence and MGM behaves like HGM. Richer evidence does not guarantee a correct or maintainable edit. Single matched budget, fixed subsets, few seeds. Sandboxed coding only; the authors explicitly warn against self-modifying agents with access to production systems or writable external storage.

### What it implies for Engram

1. **The unit of evidence for a memory update is a comparison set, not one trajectory.** Engram's consolidation works per session/episode. MGM's Φ_RM says: look at the *same* workflow across several tasks and extract the recurring pattern; Φ_CH says: look at a *sibling* that succeeded where this one failed. Both need a query Engram does not have — "other episodes that attempted the same task (or ran the same workflow), with outcomes" — and a consolidation step that consumes that set. The ledger already stores every attempt with its outcome; Episodes group them; the missing piece is the comparable-attempts query and the outcome label (RSI doc T2).
2. **The failed-task pool is a retrieval mode.** MGM's most practical trick is steering *future work* toward tasks that exposed failures so that comparisons become possible. For the PDLC layer this is ProjectMem's pre-action gate turned around: before a team starts a task, surface "this task type failed for lineage X; here is the trajectory", and record the new attempt against the same task key so the comparison exists afterwards. That needs a stable **task identity** on events (a key shared across sessions/agents), which Engram's envelope does not carry today.
3. **Genotype/phenotype maps onto Workflow node + per-task outcome record.** A Workflow version is the genotype; its phenotype is the list of task ids it was applied to and the outcome of each. Store that on the node; it is what Thompson-style selection and Recuris-style gating both consume.
4. **Version structure: keep siblings, allow two parents.** MGM never overwrites; it attaches children and lets selection decide. Engram's SUPERSEDES today (preferences) is "most recent wins", which discards the population. For Workflow/Skill nodes, SUPERSEDES should allow multiple parents (a Φ_CH child has a primary lineage *and* a donor) and record **which operator** produced the version — single-failure, cross-task, cross-lineage — as the justification. The DERIVED_FROM edges then make MGM's hand-rolled `hgm_metadata.jsonl` lineage log unnecessary: the ledger is that log.
5. **Two acceptance models, both representable.** Per-update gate (Recuris, Jev A1–A5) or population-with-posterior selection (MGM). The former suits irreversible memory mutations (merges, deletions); the latter suits procedural memory, where keeping several workflow variants alive and routing by outcome statistics is cheap. Engram can run both, because neither requires mutating the ledger.
6. **Use a reasoning model, not a coding model, for consolidation and workflow refinement.** The App. F.2 result transfers directly to Engram's LLM adapter: the extraction/consolidation model must diagnose from trajectories; coding specialisation does not help.
7. **A provenance feature emerged from evolution.** The SWE-bench agent independently evolved "track which files you viewed and constrain the diff to them". That is Engram's premise — provenance as a working tool, not just an audit trail — arrived at by selection pressure. Worth citing.
8. **Scope.** MGM evolves *harness code*. Engram should not self-modify its own code in production (the authors say the same). The transferable part is the comparative-evidence update operator applied to procedural memory, which is data.

**Verdict:** **adapt** — (a) add a `task_key` (stable task identity) to the event envelope's optional fields and a "comparable attempts" query to Consumer 4; (b) make workflow refinement consume a *set* of trajectories (same workflow across tasks; sibling success on the same task) and record the operator type on the new version; (c) allow multi-parent SUPERSEDES on Workflow/Skill and keep sibling versions with per-task outcome records instead of overwriting; (d) implement the failed-task pool as a PDLC pre-action retrieval mode; (e) choose the consolidation LLM for diagnosis ability. **Context** for harness-code evolution and for the sandboxing warning.

---

## D3. Beacon — the cross-harness self-improving memory layer (Asymptote Labs), Sep 2026

**Received as:** X post screenshot + repo link, 2026-09-25. Sources read: [repo README](https://github.com/Asymptote-Labs/agent-beacon) (MIT), [PR #574 "memory candidate review lifecycle"](https://github.com/Asymptote-Labs/agent-beacon/pull/574), [issue #620](https://github.com/Asymptote-Labs/agent-beacon/issues/620), search excerpts. beacon.sh and the blog coverage were blocked.

**What it does.** Captures full session history from 20+ coding-agent harnesses (Claude Code, Cursor, Codex, OpenCode, Cline, Devin, Gemini CLI, browser chat via extensions, cloud agents, SDKs) through OTLP, hooks, plugins and polling, and **normalises it into one OpenTelemetry-based event model**: sessions, prompts, responses, tool calls, commands, file activity, approvals, MCP interactions, token usage. Stored locally as JSONL (`~/.beacon/endpoint/logs/runtime.jsonl`), optionally forwarded to SIEMs/object stores. On top of that history: *"Run agents → capture → evaluate what worked → extract useful knowledge → review + approve → reuse across future agents."*

**The Jev step** (from issue #620). Each trace is scored with three Noul questions:

| id | question |
|---|---|
| `task_success` | Did the trace complete the user's engineering task successfully? |
| `reusable_correction` | Does the trace contain a correction or debugging pattern that future agents should reuse? |
| `evidence_supported` | Is the reusable lesson supported by concrete events in the trace? |

An application policy maps the three probabilities to **promote / review / discard**. Promoted traces become *memory candidates*; a reviewer runs `beacon memory candidates list|show|approve|reject|supersede`; approved memories are persisted in a durable store with their review transitions, and packaged as Agent Skills (`beacon-memory-recall` — read approved memory before a task; `beacon-memory-distill` — dry-run, consented evaluation, lesson drafted from the source trace). The post reports 579 sessions across 5 harnesses normalised in the demo.

**Two instructive defects.**
1. **Issue #620:** every `reason` field across 75 questions came back as the literal string `"noul"`. The rubric asked a decision model to *explain*; it cannot generate text, so approved skills carried scores but no lesson — "the installed skill cannot teach a future agent anything beyond score values." Exactly the field guide's rule and [jev-typed-decisions.md](jev-typed-decisions.md) Tier C: lesson text must come from an LLM (or the trace), Jev only gates it.
2. **PR #574 review:** re-running evaluations could overwrite reviewed candidates, resetting approved/rejected back to pending and clearing memory ids. A decision without a durable, versioned receipt is not a decision — the same gap the [catalogue](judgment-points-catalogue.md) found throughout Engram.

**What it implies for Engram.**
- Beacon is a *competitor on the capture side and a potential source on the memory side*. Its OTel-based normalised event model is what ADR-0001/0004 specified and the February research (`adr001-agent-frameworks.md`) recommended — a LangChain callback, an OpenAI-Agents tracing processor, an A2A listener — none of which Engram built. Beacon has built the collectors. Engram's differentiation is not capture; it is what happens after: provenance-bearing graph, versioned procedural memory, outcome-linked scoring, bounded retrieval.
- Its rubric is a good **first battery for Engram's episode-level gate**: `task_success`, `reusable_correction`, `evidence_supported` map directly onto the outcome label (RSI T2), the Workflow/Lesson candidate (RSI T3) and the grounding check (Jev A1). Add a fourth Noul, `instance_specific` (TRACE's de-hardcoding rule), before promoting anything to a Workflow.
- The candidate lifecycle (`candidate → approved / rejected / superseded`, with a human reviewer) is the MemTX/TARL state machine in miniature. Engram should adopt the same states on Lesson/Workflow nodes and keep the transitions as ledger events so they cannot be overwritten by a re-run (Beacon's bug).
- Beacon writes memory as skill files per harness. Engram should instead *serve* approved memory over `/v1/context` and `how_does` intent with provenance, and can ingest Beacon's JSONL as an event source rather than rebuilding 20 collectors.

**Verdict:** **adapt** — reuse the three-question rubric (+ `instance_specific`) as the first episode-gate battery; adopt the candidate lifecycle as node state with ledger-recorded transitions; treat Beacon's normalised JSONL as a candidate ingest adapter for the PDLC layer. **Context** on capture: do not compete on collectors.

---

## D4. "How Jev changes memory pipelines" — Dhravya Shah (supermemory), Sep 2026

**Received as:** X post text, 2026-09-25. Empirical, vendor-adjacent (supermemory sells a memory product); numbers are theirs, unreproduced.

**The general pipeline** the author observes across ChatGPT, Claude, Instinct, Openclaw, Hermes, Muse and customers: raw data → chunking/batching → **off-loop observation/learning** (background job, schedule or trigger) → stored context (markdown, vector, graph, KV) → summaries/profiles and search → harness injection (hooks, tools, system prompt). Engram matches this shape exactly (ledger → Consumer 2/4 → Neo4j → Atlas context).

**Findings, by pipeline stage.**

| Stage | Finding | Engram reading |
|---|---|---|
| **Reranking** (BEIR: SciFact, NFCorpus, TREC-COVID, FiQA, SCIDOCS) | Jev beat BM25 everywhere (+0.05 to +0.17 nDCG@10). **Noul-as-delete-gate failed (kept nothing)**; Noul-as-sort and a 10-level Score both worked, Score-10 best (SciFact 0.751). Beats bge-reranker-base on quality (0.612 vs 0.564) at ~20× cost; loses to jina-reranker-turbo (0.633) and to monoT5/RankGPT-4 on SciFact. Cost ≈ Voyage rerank-3. Author's call: stick with dedicated rerankers for now. | Confirms [Jev doc](jev-typed-decisions.md) B1's caution: use Score (ordered rubric) rather than a single Noul threshold when the decision is graded; and for pure reranking a distilled reranker (MemReranker, landscape §2.2) is the cheaper path. Jev's place is the *typed gate with a receipt*, not the ranker. |
| **Chunking** | Ask per sentence "does this continue the previous thought?" and cut near a target size. Best on their messy/markdown/multilingual benchmark (Chroma's chunking-eval method), ~8–10× the cost of rule-based ($0.08 vs $0.008 per 1k docs). | Engram embeds only `event_type + tool` today (catalogue I4) and never chunks content. If content embedding is added, boundary decisions are a candidate — but the PDLC sources (tickets, PR diffs, doc sections) already carry structural boundaries; rule-based first. |
| **Pre-observation filtering** | Sentence-level Noul "should this go to the extractor?" cut **58 % of content tokens**. But independent sentence classification **breaks contextuality** (assistant turns, early mentions referenced later); they could not give Jev enough context; conclusion: "Jev is not a very good compactor for memory" today. | Directly relevant to extraction cost (catalogue E1/E2: whole-session prompts, quadratic mid-session re-extraction). The lesson is *unit of judgment*: filter at turn/episode level with the surrounding state, not sentence level. Same caution as Governance Decay (landscape §2.5). |
| **Harness decisions** | Jev in Claude Code's `UserPromptSubmit` hook decides *whether memory should be injected at all* for this prompt; honours "without using memory, tell me…"; author's view: models are bad at deciding *when* memory helps, so the harness should decide, and a decision model is the right tool. | A new judgment point Engram doesn't have: **should context be retrieved at all**, and with which intent/budget. It belongs in the SDK/harness adapters (ADR-0015), ahead of `/v1/context`, and is cheap (one Noul + one Choice per prompt). Adds to the Jev map as **B0**. |

**Verdict:** **adopt** B0 (retrieve-or-not gate in the harness adapters) and the "Score over Noul-threshold for graded decisions" rule; **adapt** the pre-observation filter at episode granularity; **context** on reranking (use a reranker).

---

## D5. "I reverse-engineered Instinct's memory" — Dhravya Shah (supermemory), Sep 2026

**Received as:** X post text, 2026-09-25. Black-box probing of a commercial iMessage assistant; the author states the reconstruction may be wrong in places and is a competitor.

**What Instinct does (as reconstructed).** Memory is **git-tracked markdown files** with front-matter (`id`, `type ∈ {preference, person, organization, conversation}`, `aliases`), bodies as dated fact lists, and `[[id]]` links between files — "a densely interconnected set of files… graph-like". The answering model receives: current conversation, an identity **profile** (~4,250 tokens: life context, autonomy calibration, communication style), a memory one-pager, a compaction recap (~10k tokens), and a task board. **Retrieval is grep/keyword only** — no vectors, no BM25 — which is why every file has aliases. **Memory is read-only for the agent**; a background job (~every 24 h, inferred from a 23 h 16 min lag) reconciles: moves temporary details into workstreams, shortens durable records while linking to fuller notes, turns examples into traits, removes incidentals, replaces wrong facts with dated corrections. Old versions survive in git history and dated notes but are only found if the model looks. Forgetting is not automatic. Profile freshness lags up to two days, but dates in it let the agent discount it.

Author's rubric: single-fact recall ✅, temporal ✅, update/contradiction ✅, abstention ✅, multi-hop across sessions weak, forgetting partial, **procedural/skill memory ❌**, implicit personalisation ❌, multimodal ❌, write-side cost likely expensive (reads grow with the store).

**What it implies for Engram.**
- Three independent systems now converge on the same design: Instinct, Letta's Context Repositories (landscape §4.3) and ByteRover's Context Tree (§4.6) all use **files + versioning + background reconciliation + read-only memory for the agent**. Engram's ledger + derived graph is the same architecture with a database instead of git and a stream instead of commits. The convergence validates the split; the question is what the graph buys over files.
- What the graph should buy, and where Instinct is weak: **multi-hop across sessions** (Engram's cross-session entity bridging and CAUSED_BY traversal), **automatic forgetting** (decay tiers), **procedural memory** (Workflow nodes — absent in Instinct and in Engram's running code), **old versions surfaced by default** (SUPERSEDES with validity windows, not buried git history). These are the differentiators to make real, per the [landscape](memory-research-landscape.md) ranking.
- Two cheap ideas worth taking: **aliases as first-class retrieval keys** (Engram's `DOMAIN_ALIAS_DICT` is a hard-coded payments/devtools list; aliases should be learned per entity and stored on the node), and **dated facts** so a stale profile is self-discounting (Engram's Atlas provenance already carries `occurred_at`; make the profile/summary tier carry it too).
- The write-side cost warning ("reads grow with the store to write more") is Engram's extraction problem in another form (catalogue E9: entity resolution sees an arbitrary 1000 entities; E2: whole-session prompts). Known-entity injection scoped by alias/embedding recall, not "read everything", is the answer in both systems.

**Verdict:** **context** for the architecture convergence; **adopt** learned per-entity aliases and dated summary/profile facts; reinforces the priority of procedural memory and automatic forgetting as the differentiators.

---

## D6. Just-in-Time Memory: Learning to Curate Task-Adaptive Memory for LLM Agents — Yefan Zhou, Yang Li, Zeyu Leo Liu, Semih Yavuz, Shafiq Joty (Salesforce AI Research); arXiv 2609.27334, 23 Sep 2026

**Received as:** full PDF (25 pages), 2026-09-25; read in full.

### What it does

The paper attacks the dominant design of agentic memory — **write-time curation**: once a task ends, its trajectory is distilled into a fixed artifact (reflection, workflow, skill, reasoning strategy, memory items) that is later retrieved by similarity. Two costs: the artifact is decided *before the future query is known*, irreversibly discarding information; and one query-independent summary must serve many different downstream tasks (the same household trajectory teaches a state-change lesson to one task and a placement lesson to another). Learning a write-time curator is also hard because the value of a storage decision only shows up when a matching query arrives, possibly many tasks later (SkillOS has to group related tasks to manufacture a reward).

**JITMem** keeps the memory bank as a *passive store of raw trajectories* (task + full observation/action sequence, no abstraction) and defers curation to read time:

1. **Retrieve** top-k raw trajectories (BM25 over task descriptions only, k = 3).
2. **Curate**: a curator LLM reads the current task *and* the retrieved raw traces and synthesises a compact, task-conditioned payload (relevant memories → strategies that worked → specific guidance for *this* task). The payload is ephemeral; it is never stored.
3. **Execute** with a frozen executor, payload prepended.
4. **Update**: the trajectory is appended to the bank only if an executor-as-judge deems the task solved (quality-gated storage).

Because the payload is consumed on the same task, the curator can be trained with GRPO directly from immediate task reward — no delayed credit assignment, no task grouping, no auxiliary content-quality judge. The executor stays frozen, so one curator serves many executors.

### Results

| | ALFWorld SR | WebShop SR | τ²-bench micro |
|---|---|---|---|
| Best write-time baseline (SkillOS, RL-trained; ReasoningBank-GPT on τ²) | 61.2 | 16.5 | 71.7 |
| **JITMem** (Qwen3-8B curator, RL-trained) | **77.4 (+16.2)** | **32.8 (+16.3)** | **75.6 (+3.9)** (untrained, GPT-5.4 curator) |
| JITMem-base (untrained) | 60.5 | 11.7 | 68.9 |

Key findings: (i) **even an untrained read-time curator matches or beats write-time methods** using the same model (WebShop with Gemini-2.5-Pro: 61.0 vs ReasoningBank 40.2 / SkillOS 41.0) — task-adaptive read-time curation is itself the main source of gain; (ii) the trained curator **transfers across executors** (trained with Qwen3-8B, within 1.4 SR of one trained with GPT-5.4); (iii) payloads are **compact**: +1.9K input tokens over no-memory vs +10.7K (ReasoningBank) and +13.4K (SkillOS), and 28–31 % fewer executor steps; (iv) **ablations**: removing task conditioning −3 to −11 SR; storing all trajectories with success/failure labels instead of filtering to successes −1.5 to −3.4; applying ReasoningBank-style distillation at write time instead of storing raw traces **−1.7 to −8.2**; removing retrieved trajectories from the trained curator −15, so RL learns to distil retrieved experience rather than to hallucinate hints; (v) memory helps most where tasks need **synthesised procedural guidance** (τ² Telecom +11.0); on fact-retrieval-shaped domains (Airline, Retail) no memory method beats no-memory beyond variance. The curator prompts all carry a de-hardcoding rule ("do not copy concrete identifiers… always look up the current case"); the judge prompt credits only outcomes that tool results confirm. Limitations (authors'): BM25 retriever may bottleneck at scale; one extra LLM call per task; payload format hand-designed per benchmark; curation once per task, not per step.

### What it implies for Engram

This is the most direct challenge to Engram's design among the papers so far, and it is partly right.

1. **The ledger is a JITMem memory bank already.** Engram stores every event losslessly and forbids mutation; the paper's central claim — *never discard at write time* — is ADR-0004. What Engram lacks is the read side: nothing in the read path synthesises a task-conditioned payload from raw events. `/v1/context` returns scored nodes; `/v1/query/subgraph` returns a bounded subgraph. Both are *selection*, not *curation*. The Context Compaction Theory paper (landscape §2.4) makes the same point from the other direction: generation can need strictly less budget than selection.
2. **Engram's write-time layers are exactly what the ablation penalises — if they are treated as the payload.** Consumer 2 (session-end extraction into Entity/Preference/Skill nodes) and Consumer 4 (episode/session summaries) are write-time distillation. The reconciliation is MemIR's (landscape §1.3): raw Events are *evidence*, the projected graph is *retrieval cues and structure* (which entity, which causal chain, which episode), and the Summary tier is a *cache* of common curations — none of them should be the only thing an agent can read. Today the whole retrieval path returns projections and never the raw payloads behind them (`payload_ref` is a pointer the read path does not follow). Fix: a read-time **curate** step that follows `payload_ref` for the selected Events and synthesises a task-conditioned briefing, with the graph used to *pick* the events, not to *summarise* them. Provenance carries through: the briefing cites the event ids it was built from.
3. **Quality-gated storage vs the immutable ledger.** JITMem stores only judged-successful trajectories and shows that storing everything with labels is worse (the curator "cannot fully suppress the noise"). Engram must keep everything (audit, replay, GDPR, ReasoningBank-style failure lessons). Resolution: the ledger keeps all; the **procedural retrieval bank is a filtered view** — Episodes with `outcome = success` (RSI T2's outcome event) are what the curator sees by default; failures are retrievable on request for negative-evidence lessons (RSI T3). This is the same "filter at storage time provides a cleaner retrieval signal" result, implemented as an index rather than a delete.
4. **Where read-time curation belongs, and where it does not.** It adds an LLM call per task, which violates the zero-LLM hot-path rule that Eywa and Engram's own design share. It belongs behind the **B0 gate** in the harness adapter ([Jev doc](jev-typed-decisions.md)): fire it at *task start* for `how_does`-shaped requests (the τ² Telecom result says that is where it pays), not on every `/context` call for fact lookups. The payload is ephemeral, but its **receipt** (query, event ids used, curator model, payload digest) is a ledger event — that is the retrieval receipt RSI T2 needs, and it makes outcome feedback attributable.
5. **Read-time and write-time are not exclusive; they are the two ends of the RSI loop.** Write-time curation (Workflow induction, MGM-style comparative refinement, digest D2) produces *candidates* for what will be useful; read-time curation produces the *instance* for this task. The paper's own τ² payload shows the curator re-deriving an ordered diagnostic procedure from three raw transcripts on every request — exactly what a promoted Workflow node would cache. The right design: curate at read time from raw evidence; promote recurring curations to Workflow nodes with outcome statistics; let the curator retrieve Workflows *and* raw Episodes and choose. That keeps the paper's advantage (nothing lost, task-conditioned) and Engram's (versioned, provenance-bearing procedural memory).
6. **Trainable curator = a component Engram can own.** A single small curator (8B) trained once on task reward transfers across executors. For the PDLC layer, "executor" is whichever coding agent the team uses (Beacon's 20 harnesses, digest D3); a curator trained on merged-PR outcomes would be the Engram-owned model in the loop, with the ledger as its training bank and the retrieval receipt as its reward link.
7. **Retriever note.** BM25 over task descriptions only, k = 3, insensitive to k. Engram's BM25 channel is dead (scale D2) and its query embedding never sees content (catalogue I4). A `task_key`/task-description index is cheap and is what both MGM and JITMem retrieve on.

**Verdict:** **adopt** — (a) a read-time `curate` step over raw event payloads for task-start requests, behind the B0 gate, with an ephemeral payload and a ledger receipt; (b) an outcome-filtered procedural view of Episodes as the curator's default bank; (c) a task-description index for retrieval. **Adapt** — reposition Consumer 2/4 outputs as retrieval cues and cached curations, not the sole read surface; make the read path able to follow `payload_ref`. **Context** — the curator-training recipe (GRPO on immediate task reward) as the long-term Engram-owned model.

**Tension to record in an ADR.** ADR-0003 calls the Neo4j projection "query-optimised". This paper shows that for procedural memory the query-optimal representation is *raw traces plus a task-conditioned reader*, not a pre-abstracted graph. The graph remains right for lineage, entity and cross-session questions (MOOSEDev, landscape §6.3, is the counter-evidence in Engram's favour on supersession/negation queries). Both should be stated.

---

## D7. "Self-Improving Agents" daily brief — X-pipeline snapshot, 2026-09-25

**Received as:** a claude.ai artifact (insights / trends / glossary / raw feed; 245 posts, last 45 days). Secondary source: social posts summarising papers and product launches; nothing here is reproduced. Items worth a primary read are flagged **[fetch]**.

### The brief's five insights, and what Engram should take from each

| Insight (brief's wording, condensed) | Evidence cited | Engram reading |
|---|---|---|
| **Memory is getting a System-One controller; the LLM is leaving the hot path.** | **Jev-Mem** (arXiv 2609.23986): a System-One controller owns memory *typing, routing, budgeting, graph scoring and stopping*; LoCoMo LLM-judge 0.777 (+11 %), memory build 158 s (6.6× faster than the fastest competitor), query ~0.93 s. Supermemory put Jev on the recall/no-recall gate (digest D4); Vectorize's Hindsight shipped Jev reranking. | This is the [Jev map](jev-typed-decisions.md) taken to its conclusion — a two-tier stack where a decision model governs what enters and leaves context and every read/write is a logged, scored decision. Engram's version already exists on paper (Tier A gates + B0/B1); Jev-Mem is the first system to report numbers for it. **[fetch]** the paper: it is the closest published design to "receipts + gate + budget" and will say what the controller's question battery looks like. |
| **Typed decisions displace LLM calls on bounded label sets — not yet inside open-ended agent steps.** | Deel: repeat-question matching 70 → 97 %, expense categorisation 50 → 86 %; MotherDuck `prompt_jev()`: 100k rows for $0.50 vs $37. **Counter-evidence:** a builder tested six Jev-style fast actions inside a coding agent and "none survived… too unreliable". | Confirms the boundary drawn in the Jev doc: use it on closed taxonomies (intent, source type, relation type, promote/review/discard) and on gates, not on open agent choices. The PDLC layer's decisions are mostly closed (ticket state, link type, supersession relation) — good fit. |
| **Retrieval is becoming a learning signal: memory rewires on what helped.** | REALM (+7 LoCoMo, reconsolidates the activated subgraph after recall); **Hippo-memory** (TypeScript + SQLite, decay + retrieval strengthening + consolidation, MCP for Claude Code/Cursor, 74 % R@5 on LongMemEval with BM25 only); **Hindsight** (Vectorize, self-hosted, retain / recall / reflect, "recall isn't learning", LongMemEval SOTA claim with reproduction notes). | Three more data points for RSI T2 (reinforce on *helped*, not *returned*). Note the brief's own watch item: feedback loops where frequently-recalled-but-wrong memories get reinforced — exactly why the outcome signal, not the recall signal, must drive `S_boost`. Hippo-memory's number is a useful floor: BM25 + decay + strengthening alone reaches 74 % R@5. Engram's BM25 channel is dead (scale D2). |
| **RSI is being measured, monitored and legislated before anyone has shown it compounding.** | A Google paper lets agents rewrite their entire harness (prompts, tools, memory, control flow, subagents) — read by builders "as a warning label"; Microsoft measures *agent taste* (picking the better branch mid-task); Mallen: continual learning erodes blocking monitors; a five-level RSI taxonomy says meta-improvement is undemonstrated; Anthropic proposes a pause framework; a US bill would ban RSI. | Reinforces the [RSI positioning](rsi-positioning.md) §4: Engram evolves *data* (memory, workflows), never its own code in production; every step auditable and reversible from the ledger. That is a governance story, not just an engineering one, and it is now a selling point. "Agent taste" (mid-task branch choice) is a metric the PDLC layer could expose from receipts + outcomes. |
| **The judge got 200× cheaper and lost its reasons.** | One week of Jev replacing Gemini 3.1 as a pass/fail eval judge: same accuracy, ~200× cheaper ($0.01 → $0.00005), ~50× faster (10 s → 0.2 s); Datadog runs online + offline evals with Jev. Cost: verdicts are thresholded probabilities with no explanation, so "a score regression arrives without evidence" and it is harder to tell improvement from judge-gaming. | Same lesson as Beacon's `"noul"` bug (D3): keep the reasons elsewhere. For Engram's eval loop: cheap continuous judging is now affordable at every consolidation cycle, but the receipt must carry the state digest and the evidence ids so a regression can be explained after the fact; and the RSI loop must not tune against the judge it is scored by (frozen judge, held-out split — T5). |

### Other items from the feed worth noting

- **EvoSkill** (Sentient): turns failure traces into reusable skills with the model frozen; the feed claims 60+ citing papers. Another instance of the failure-derived lesson / negative-evidence node (RSI T3). **[fetch]**
- **CL-Bench** (Asawa et al., UC Berkeley / Snorkel, Jun 2026): measures continual-learning gain across repeated tasks; best reported gain 25.4 %. A candidate outcome-linked benchmark for H4/H6 in the discovery plan. **[fetch]**
- **GLiNER2.5-Decide**: an open compact-encoder decision model builders frame as the open alternative to Jev. Relevant to the vendor-concentration risk in the Jev doc §6 — the `ports/decision.py` interface should have a second adapter.
- **Hindsight + Hippo-memory** join Instinct / Letta / ByteRover / MemPalace as local-first, LLM-light memory layers exposed over MCP. The market is converging on "own the store, keep the LLM off the hot path"; differentiation is in versioning, provenance and procedural memory — Engram's stated ground.
- **Jev signup pause / rate limits** are flagged as an adoption cap; another reason the decision port must fall back to rules.

**Verdict:** **context** for the brief as a whole; **adopt** the two-tier framing (decision controller + LLM reasoner) as the explicit architecture statement in the next ADR; **fetch** Jev-Mem, EvoSkill, CL-Bench for primary digests when intake resumes.

---

## D8. Memory-stack evidence bundle — systematic catalogue behind the daily brief, built 2026-09-26

**Received as:** four Markdown files (README, synthesis, evidence ledger, single-file bundle), now stored under [`evidence/`](evidence/README.md). Built from the 26 evidence items behind the brief in D7: 86 X posts with threads, 2 X Articles, **5 arXiv papers read in full** (Jev-Mem 2609.23986, REALM 2609.16053, EvoSkill 2603.02766, RRSI 2609.24972, RSI levels 2609.11873), **4 repos read at pinned commits** (Hindsight, Hippo-memory, Beacon, lintpal), ~15 web pages, 26 transcribed images. Every claim points to a source note with a strength rating. This supersedes D7 wherever they differ.

### Corrections to D7 (from the bundle's contradictions table)

| D7 said | The sources show |
|---|---|
| Hindsight updates memory on read | It does not. Recall writes nothing; the unused `access_count` column was dropped in Aug 2026. Learning happens at write time. |
| Hippo-memory 74 % R@5 | Stale v0.11 BM25-only figure; current 98–99.8 % per haystack. Its own audits: age decay had **no measurable effect**; sleep consolidation **cost 3.6 points**. |
| Beacon "Jev as a write gate" | A candidate filter in front of human review: `task_success ≥ 0.50` AND mean of three Nouls `≥ 0.60`; the `task_success` floor was added after a failed task averaged through (issue #649). No quality metrics. |
| Supermemory "58 % token reduction" | Applies only to the pre-extraction filter, which also produced a wrong memory ("i love that stuff" attached to the wrong food). |
| REALM +7 LoCoMo | Correct vs MAGMA, but **reconsolidation itself adds only +2.0**; the knowledge-update gain (84.7 → 88.9 vs Zep 74.4) is driven by write-time `supersedes`/`contradicts` edges and the rule "prefer add over modify; never merge a state change". |
| Deel 70→97 %, 50→86 % | Also −16.6 on metric picks and −3.6 on 3-level root-cause tagging; expense baseline is rule-based, not human. |
| Jev-Mem +11 %, 6.6× | Numbers check, but one benchmark (text says two), no ablations, no cost, no variance, text/table disagree in four places. |

### What the bundle establishes (evidence strength in brackets)

**Write path.** Admit everything; spend decisions on *structure*, not admission [Jev-Mem, 1 benchmark]. Jev-Mem's recipe: type each observation with four Nouls (`episodic / semantic / procedural / preference`, overlapping scores, not a category); pick ≤10 candidate neighbours deterministically (vector + lexical + entity + time); confirm typed edges (`semantic`, `caused_by`/`causes`, same-episode, entity-equivalence only when ids don't match) at **score ≥ 0.60**; timestamps and exact entity ids create edges with no model call. Write `supersedes`/`contradicts` **at write time** [REALM, ablated]. Gate *promotion* to durable lessons, not storage [Beacon]. Do not put the decision model inside the extractor at sentence granularity [Supermemory's own counter-example]. Treat every skill write as a proposal that must beat the current best on a held-out split; reject entries that name specific eval tasks/entities/answers (leakage) [EvoSkill, RRSI].

**Read path.** Fuse vector + BM25 + entity + time with RRF k=60 [Jev-Mem, Hindsight — two independent designs]. **Rerank listwise in one call**: one Choice over the pool gave recall@1 0.94 vs 0.87 for one Noul per candidate, with 30× fewer calls; vs local MiniLM at 30 candidates 0.950 vs 0.800 [Hindsight, LoCoMo-200, vendor]. Jev scores are rank positions within a call, not absolute relevance — never port a score floor. **Never give a gate a "nothing relevant" option**: "none of these" emptied 35/200 queries; a "nothing" level cut gold retention 0.81 → 0.65; pruning lifted precision 0.05 → 0.85 but dropped 19 % of gold — always return ≥1, pruning off by default [two teams]. Counterweights: six self-hosted rerankers matched Jev's nDCG@10 (~0.746) on SciFact at ~1/10 the cost; Hippo found Jev reranking no better at *answering* than a free cross-encoder.

**Stopping.** Replace fixed top-k with a sufficiency rule: stop when `evidence_sufficient ≥ 0.95` and `missing < 0.15` and `contradiction < 0.15`, or `continue_useful < 0.15`; hard caps depth 8, 60 nodes, 2400 edges, 16 controller calls, 15 s; six routing Nouls split an expansion budget of 80 across the four relation views [Jev-Mem — the most complete control design in the set, **no ablation**].

**Update on read.** The weakest trend. Only REALM does it properly: reweight or add edges, never rewrite content or delete; bounded `w += η·c·(1−w)`; retrieval uses `0.6·sim + 0.4·w`; **+2 points**. Feedback loops (wrong memory recalled → strengthened) are **unmeasured everywhere**; REALM uses the same model to answer and to audit.

**Consolidation and forgetting.** **No source implements real forgetting.** Jev-Mem records obsolescence and never acts on it; REALM and Hindsight have no decay; Hippo's decay did nothing measurable. Jev-Mem's consolidation: every 20 writes, one Choice `keep_separate / merge / promote / uncertain`; call the LLM summariser only at ≥ 0.85; raw observations always kept. From the RSI papers: raw trajectories often beat distilled skills; generated skills sometimes make results worse.

**The decision model.** Calibration is claimed, not shown: Jev-Mem's authors say scores "are not assumed to be calibrated probabilities" and threshold them anyway; Datadog logged values of 1.10 and 1.06. Fit thresholds on your own data; log raw probabilities; pin the model; keep thresholds in code; minimal state. Failures: Deel −16.6 on messy metric picks; six fast actions in a coding agent all dropped (small samples; only "is the goal done?" looked promising). Hosted and fails closed → keep an RRF/LLM fallback.

**Evaluation.** Strongest field result in the set: one week of Jev as pass/fail judge replacing Gemini 3.1 — no accuracy change, ~200× cheaper, ~50× faster; threshold > 0.8, an LLM explains only the failures; a full run costs $0.14–0.20, so latency not money decides per-PR gating [Sentry]. RRSI discipline: run the unchanged stack several times and use the spread as the minimum gain a change must beat; charge memory for its tokens; one attributable change per round; keep the experiment ledger *outside* memory. Gaps: Jev-Mem one benchmark; REALM excluded unanswerable questions; nobody tests abstention, feedback loops or forgetting.

**Oversight.** A memory that learns from outcomes will route around guardrails without intent [Mallen]: tag writes from blocked episodes; treat a falling guardrail-trigger rate as a warning; keep one check that never feeds memory. On the B0–L5 RSI ladder, EvoSkill/RRSI sit at L2 (fixed objective and evaluator, AI chooses edits); keep the evaluator outside the memory write path to *stay* at L2 deliberately.

### What changes for Engram

1. **SIMILAR_TO / CAUSED_BY / RELATED_TO creation finally has a recipe.** Nothing in Engram creates SIMILAR_TO today (catalogue I4/C7). Jev-Mem's write path — deterministic top-10 candidates, decision-confirmed typed edges at ≥ 0.60, deterministic temporal/entity edges — is a drop-in design for Consumer 3 and replaces the dead `SIMILAR_TO < 0.7 prune` with an admission threshold that actually runs. Store the edge probability as the edge weight (REALM's `w`).
2. **Jev map corrections.** B1 (neighbour admission) becomes a **listwise Choice over the candidate pool, always returning ≥1**, not a per-candidate Noul with a threshold, and never with a "none" option. B0 (retrieve-or-not) stays as a separate, upstream gate. A3 (delete/archive) stays a Score. Add a **stop rule** as a new retrieval judgment point (there is none today; `max_nodes` is the only bound).
3. **Forgetting is genuinely untested ground — including Engram's.** Every system in the bundle either has no decay or found it did nothing. Engram's four-tier decay is an untested hypothesis, not a differentiator, until H2/H4 in the discovery plan measure it. Until then: reweight, never delete; archive-before-delete enforced by code.
4. **Write-time `supersedes`/`contradicts` is the knowledge-update lever**, not read-time reconsolidation. That is Engram's Belief lifecycle (landscape §1.11–1.14) — priority confirmed, mechanism narrowed: edges at write time, "prefer add over modify".
5. **Eval discipline for the autoresearch loop**: RRSI's noise floor, token charge, one change per round, external ledger, plus a held-out set with knowledge-update, contradiction and abstention questions. This is the concrete fix for catalogue V7/V8.
6. **Governance rule set**: tag memory writes originating in blocked/denied episodes; monitor guardrail-trigger rate; one check outside the memory path. Cheap, and it is what keeps Engram at L2.

**Verdict:** **adopt** items 1, 2, 5, 6; **adapt** 4 into the Belief-lifecycle design; **context** for 3 (it is a warning). The bundle's §9 "starting configuration" and this pack's six-layer stack agree on every point except that the bundle adds the stop rule and the "never return nothing" rule — both now taken.

---

*Next entries are appended below as papers arrive.*
