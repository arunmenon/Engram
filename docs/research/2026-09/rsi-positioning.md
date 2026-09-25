# Engram and recursive self-improvement (RSI)

**Date:** 2026-09-25
**Source of the taxonomy:** "An RSI Taxonomy" by Yaowei Zheng (LlamaFactory), September 2026, shared as screenshots; it draws on the *Awesome RSI* repository. Individual systems are characterised from their primary papers in [memory-research-landscape.md §7](memory-research-landscape.md#7-recursive-self-improvement-memory-and-skill-evolution).
**Companion:** [judgment-points-catalogue.md](judgment-points-catalogue.md) for the code references; [jev-typed-decisions.md](jev-typed-decisions.md) for the decision layer.

## 1. The taxonomy, in Engram's terms

The article defines RSI as: after interacting with an environment, an agent uses task trajectories and feedback to modify its own state through an update mechanism, and the updated state participates in later tasks —

    A(t+1) = U(A(t), τ(t), f(t))

with **Agent = Model + Harness**, and Harness = context, memory, skills, tools, harness code. Context is what the model sees during the current inference; memory is what is stored externally and becomes context only once retrieved and inserted.

Dimensions: **what evolves** (parameters / context / memory / skills / tools / harness code), **how versions evolve** (chain / tree / graph), **who updates** (self / teacher / joint), **when** (offline / online / hybrid), plus acceptance criteria, feedback source, feedback type, update frequency and experience scope.

| Taxonomy element | Engram today | Engram's natural role |
|---|---|---|
| τ — trajectory | the immutable event ledger (Redis Streams) | **the trajectory store**, with global ordering and provenance |
| Memory (harness) | Neo4j projection: Event, Entity, Summary, UserProfile, Preference… | **the memory store** an update mechanism writes into |
| Skills (harness) | Workflow, BehavioralPattern, Skill node types declared; no code creates them | **the procedural-memory store** |
| Context | `/v1/context` and `/v1/query/subgraph` responses | **the memory→context boundary**: bounded, scored, provenance-annotated context assembly |
| f — feedback | `access_count++` on return; ±1 `/v1/feedback` | *missing*: no outcome signal reaches memory |
| U — update mechanism | ad hoc: overwrite persona, overwrite proficiency, "most recent wins" | *missing*: no explicit, gated, versioned update operator |
| Version structure | DERIVED_FROM, SUPERSEDES, SUMMARIZES edges (partly implemented) | **Graph** — the strongest of chain/tree/graph — and replayable from τ |
| Model parameters | out of scope | out of scope; Engram is model-agnostic |

**Positioning statement.** Engram is not an RSI system. It is the *substrate* an RSI update mechanism writes into: the trajectory store, the versioned memory and skill store, and the memory→context boundary. Every memory-evolving system in the taxonomy's table has to invent its own storage, versioning and provenance; Engram already has the ledger, the derived graph and the lineage edges. The claim Engram can make that none of them can: **every self-improvement step is auditable and reversible from the ledger.**

## 2. What the article's §2.2 and §2.3 add

**§2.2 Context evolution (Prime Agent).** Context evolution "removes irrelevant information, compresses an overlong history, adds lessons from failures, or rewrites the current plan". In Engram that is the read path plus the summary tier: the bounded, scored context is the evolved context; Summaries are the compressed history; there is currently no "lesson from failure" node and no "current plan" node. Prime Agent's *Continual Harness* — recording "task history, memory, skills, prompts and sub-agent configurations" so work "resumes from where it stopped without rereading everything" — is a description of an Engram client. The PDLC use case (multi-hour, multi-session, multi-agent work over code and documents) is exactly the long-horizon setting the section describes.

**§2.3 Memory evolution (ReasoningBank).** The loop is: retrieve relevant strategies → act → **an LLM-as-judge determines whether the task was completed** → extract memory items (title / description / content) from **both successful and failed** trajectories → consolidate. Two things Engram lacks are named here: (i) the judge step — an explicit success/failure decision per trajectory that becomes `f(t)`; (ii) **negative evidence** — "failed trajectories record decisions that should be avoided". Engram has no node for a lesson-from-failure or an anti-pattern. MaTTS (several attempts at the same task to produce contrastive signal) is only possible if the store keeps every attempt with its outcome — which the ledger does.

## 3. Tenets to plug in, ranked by leverage

### T1. Make `U` explicit: proposal → gate → committed version, all on the ledger

Today derived memory is mutated in place (catalogue E8, E16, E17, C5) with no record. The 2026 systems with the largest reported gains all gate updates on outcome evidence (Recuris validation gate; TRACE contrastive rounds + de-hardcoding rule; SkillSmith anti-pattern veto; MediSkill-Evo typed validation; Memp deprecate). Concretely:

- Every mutation of derived memory (extracted item, merge, supersession, importance change, deletion, workflow promotion) is emitted as a **proposal event** on the ledger (`memory.proposal.*`).
- A **gate** decides: deterministic checks first, then a typed decision (see Jev A1–A5), then policy. The decision is a **receipt event** (`memory.decision.*`) with state digest, battery version, model id, distributions, thresholds.
- Only then is the projection written, carrying the receipt's id as provenance. Versioning uses MemTX's lifecycle (`raw → tentative → validated → committed → action-safe → quarantined → superseded → revoked`) as node state, and TARL's action vocabulary (`add / ignore / revise / reject / defer`) as the gate's output.
- **Extend SUPERSEDES** from Belief→Belief to Workflow→Workflow and Skill→Skill so procedural memory has versions with a stated reason.

This is also what makes Engram's version structure a *graph* in the taxonomy's sense rather than a chain of overwrites.

### T2. Close `f(t)`: outcome feedback, not retrieval feedback

Engram's only signal is "returned ⇒ `access_count++`" (R19), which is not feedback. Oblivion's rule is "reinforce what contributed to the answer, not what was retrieved". For PDLC the outcome signals are cheap and unambiguous: PR merged, CI green, ticket closed, review approved, spec accepted, test passed. Requirements:

- A **retrieval receipt**: which memories were served for which query/task/session, recorded as an event. The catalogue found none exists; the Jev receipt and this receipt are the same primitive.
- An **outcome event** (`task.outcome`) that references the retrieval receipt(s).
- A propagation rule: outcome → served memories → `S_boost` (Ebbinghaus stability) and success/failure counts on Workflow/Skill nodes. Teacher-verified outcomes (human reviewer, merged PR) weigh more than agent self-reports.

ReasoningBank shows the judge need not be perfect (robust at 70–90 % judge accuracy); a typed Noul "was the task completed given `evidence`" is enough where no hard signal exists.

### T3. Skill evolution: make procedural memory run

Workflow / BehavioralPattern / ABSTRACTED_FROM are declared and dead (B3). The RSI literature's Memory/Skill column is the roadmap:

- **Induce** workflows from successful Episodes (AWM), at two granularities: step-level and script-level (Memp).
- **Store** as ReasoningBank items — title, description, content — with outcome label, support count, success/failure counts, DERIVED_FROM to the Episodes, and TRACE's rule that a stored workflow may not contain instance-specific values.
- **Refine** contrastively between rounds (TRACE) and **localise** a failure to one node before patching (Recuris).
- **Deprecate** on repeated failure (Memp); **veto** proposals that match a known anti-pattern (SkillSmith) — which needs a **negative BehavioralPattern** node type (`polarity = avoid`).
- **Serve** on `how_does` intent; MemOS's L1 traces → L2 policies → L3 world models is the abstraction ladder Event → Workflow → BehavioralPattern.

For PDLC this *is* the product: "requirement → HLD → LLD → tickets → PR" is a workflow each team executes repeatedly and the system should learn the team's variant.

### T4. Who updates: keep self- and teacher-updates provenance-distinct; never let the proposer accept

Self / teacher / joint maps onto Engram's source-type confidence ceilings (explicit vs inferred). But the extraction LLM assigns *its own* source label and hence its own ceiling (E2/E6). Rule: the proposer never grades itself — an independent typed judge (Jev A1) or a human sets the ceiling. Agent self-reports start **silent** (Microsoft's engram maturation: low activation until corroborated); teacher-verified memories get a stability boost.

### T5. When: Engram is hybrid — name it, and fix the offline loop

- Online: per-event projection, access reinforcement, feedback. Add REALM-style retrieval-triggered reconsolidation.
- Offline: 6-hour consolidation, pattern detection, and the autoresearch parameter tuning — which is the taxonomy's *harness-code evolution* cell (Gödel Agent / DGM). The catalogue found the classic failure mode: the proposer can rewrite the judge (`evaluate()`), the harness leaks gold labels, and acceptance is "score > best" with no held-out set (V2, V3, V7, V8). Fix: frozen judge; held-out split; D²ACCI-style paired-stats gating; margin and repeats; the judge's own provenance recorded.

### T6. Experience scope: which experiences may a memory learn from?

Per user, per team, per tenant, cross-tenant. This lines up with ADR-0027 grants and AkasicMEM's "authorization continuity" (source restrictions survive derivation). A team's workflow must not leak across tenants; anonymised structural patterns might. Scope is a property of the proposal, checked at the gate.

## 4. What not to adopt

- **Model-parameter evolution** (SEAL). Out of scope.
- **Online harness-code self-modification in production.** Keep it offline, sandboxed, judge frozen.
- **Ungated memory rewriting** (A-MEM-style "new note rewrites old notes"). It is the lowest-scoring pattern in the 2026 comparisons and it destroys provenance.
- **Ranking by a decision model's raw probability across items.** Gate with typed decisions; rank with Engram's own scoring.

## 5. A caution on measurement

A graph memory with a pruning formula almost identical to Engram's lost to a flat vector baseline on LongMemEval at matched budget (landscape §1.17). Any RSI loop that tunes forgetting or retrieval needs a benchmark that can see graph lift and has no label leakage: MemDelta's one-variable protocol, ForgetEval, MemOps, MemTrace, and — for PDLC — DreamBench-SWE and LongMemEval-V2's workflow-knowledge questions.

## 6. Minimal implementation order

1. Retrieval receipt + outcome event (T2) — two event types, no schema break.
2. Proposal/decision events and node state (T1) — new event types, new node properties with defaults; frozen models untouched.
3. Workflow induction from Episodes with success counts, SUPERSEDES on Workflow (T3) — Consumer 4.
4. Independent acceptance judge for extraction (T4 + Jev A1).
5. Frozen-judge, held-out eval loop (T5) — replaces the current autoresearch acceptance rule.
