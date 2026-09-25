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

*Next entries are appended below as papers arrive.*
