<!-- Received 2026-09-26 from the external reviewer (Codex), pasted verbatim by the author. Reviewed review-prompt-pillars.md and t0-intelligence-handbook.md. -->

1. **Keep the research areas, but separate topic labels from beliefs. Confidence: high.**
   - R1–R7 currently mix subjects, favored mechanisms, empirical claims and product requirements. Agents should not have to believe “read-time curation wins” to classify a retrieval paper.
   - Use a stable taxonomy, a separately versioned belief register, and individual experiment cards. Changing a belief should not require relabeling the archive.
   - Assign one primary pillar by the claim being tested, optional secondary pillars, and separate tags for mechanism, workload, lifecycle stage and evidence type.
   - Boundaries: **R1** evidence identity/preservation; **R7** cross-store compatibility. **R2** durable state changes; **R3** request-time evidence selection. **R5** learning from experience; **R6** whether an evaluation supports its conclusion. A paper can contain several claims with different labels.

2. **Add R8: trust and governance. Treat shared-agent operation and economics as mandatory cross-cutting dimensions. Confidence: high.**
   - **Security/injection:** deserves an owner and pillar. Identity, authorization, suppression, malicious evidence and execution authority are not merely scorer quality. The research company itself consumes adversarial external text.
   - **Multi-agent/shared memory:** currently a real gap. Tag all applicable claims `shared_state`; investigate ownership, conflicting writes, handoffs, attribution and recovery under R1/R2/R7/R8. Give coordination its own pillar only if the research volume warrants it.
   - **Cost/latency:** require full lifecycle cost and a workload/SLO on every experiment. A separate pillar is unnecessary initially; queue economics also need an operational owner.
   - **Human review/certification:** R2 owns promotion states; R8 owns who may authorize them. Standing policies can automate routine decisions; uncertain or high-impact exceptions need an explicit escalation path.
   - **Ontology:** R1 owns evidence semantics and identity; R7 owns mappings and compatibility. Do not make the gateway owner of every domain ontology.
   - **Missing product signal:** include actual adopter failures, incident evidence and rejected workflows alongside social signals. A research company needs a demand/problem register as well as a literature register.

3. **Several “beliefs” should be narrowed or moved out of the taxonomy. Confidence: high for the corrections; field results remain unverified.**
   - **R1:** “no surveyed system” must name the survey and date. Document-level retriever traces already exist; that is weaker than durable authorized replay, but invalidates broad novelty wording. [LangSmith](https://docs.langchain.com/langsmith/log-retriever-trace)
   - **R2:** REALM's 84.72→88.89 is reconsolidation off/on, not an isolated write-time-edge effect. Its base versus Zep is a whole-system comparison. A negative aggressive-summary result does not eliminate other consolidation mechanisms. Replace “never delete” with versioned corrections plus explicit retention, suppression and erasure policies. [REALM Table 3](https://arxiv.org/html/2609.16053v1#S4.SS3)
   - **R3:** matches on retrieval roots are not matches on tokens. There is now a relevant provenance-graph result with candidates and seeds controlled; test transfer instead of fixing the graph's role in advance. [Execution Provenance](https://arxiv.org/abs/2609.25913)
   - **R4:** the listed numbers come from different tasks and evidence qualities. They do not establish a universal listwise policy, escalation rule or calibration. Preserve exact sources and conditions; field reports are leads until verified. Always permit insufficient evidence where the task allows it.
   - **R5:** “will route around guardrails” is an unproven universal claim. State a measurable failure risk. “Unmeasured in every published system” exceeds a bounded survey.
   - **R6:** “four in five” needs its audited denominator, selection method and coding rules. Zero false positives in 22 independent trials gives a one-sided 95% upper bound around **12.7%**—weak evidence, not literally no information. A frozen judge can still be biased.
   - **R7:** one enterprise's contract establishes local demand. It cannot establish universal product fit or global absence of federated snapshots. Define the required snapshot level before comparing systems.

4. **Rewrite the reversal criteria around decisions, not the arrival of any paper. Confidence: high.**
   - **R1:** after source mutation, reproduce the served evidence using native retained versions versus copied artifacts; include unavailability and revocation. Measure replay success, cost and policy violations.
   - **R2:** replay an update stream through one clearly specified lifecycle mechanism and its disabled baseline; test current/as-of accuracy, recoverability and storage cost.
   - **R3:** compare hybrid retrieval, typed traversal and curation on the same source units and token budget, including long documents and unanswerable tasks.
   - **R4:** compare rules, a local scorer and an optional remote scorer on one decision's error cost, abstention, latency and shifted inputs.
   - **R5:** compare reviewed playbooks, raw episodes and induced procedures on held-out task families. Keep outcome attribution observational until controlled exposure is possible.
   - **R6:** inject known leakage and judge-bias defects into a test harness; require the audit to detect them, then check model conclusions against blinded human or executable judgments.
   - **R7:** change between two actual backends without harness edits and exercise unsupported capabilities, partial failure and historical reads.
   - **R8:** submit poisoned evidence, replay another agent's action, revoke permissions and restore old state; require bounded, authorized behavior.
   - For each, predeclare what action a positive, negative or inconclusive result changes. Finding another system is competitive evidence, not by itself a falsification of usefulness.

5. **Keep R5 as a research area; remove procedural memory's assumed product priority. Confidence: medium-high.**
   - “Learning from experience” is a coherent question even if its implementation is deferred. It covers useful negative results, delayed outcomes, transfer and harmful reinforcement.
   - Give it a watch budget rather than a large execution budget this quarter. Otherwise popular self-improvement posts will constantly reopen a decision to defer it.
   - The research company's own history is a useful controlled workload: can agents avoid repeated failed experiments without suppressing justified reruns? That creates a concrete study without assuming a procedural-memory product.

6. **R4 survives only if renamed and specified around decisions and uncertainty. Confidence: high.**
   - Use **Decision quality and abstention**. Rules, classifiers, NLI, rerankers, larger models and human review are candidate implementations.
   - A vendor is a source tag, not a research boundary. Collect counterexamples and open implementations through mechanism-based queries.
   - Closed outputs constrain syntax. They do not establish that a label is knowable. Evaluate “unknown,” partial evidence and escalation on the selected borderline population.

7. **Work R1, R6 and R7 deeply this quarter; enforce R8 across all work. Confidence: medium.**
   - **R1:** prove what was served can be reconstructed with provenance.
   - **R6:** make the experiment factory trustworthy before it manufactures conclusions.
   - **R7:** prove usefulness across the adopter's real stores and agent handoffs.
   - Use R2/R3 minimally inside that slice; shadow at most one R4 scorer; keep R5 exploratory. R8 correctness requirements are mandatory, while research into new safety mechanisms can remain bounded.
   - Keep a small exploration allocation for out-of-taxonomy findings. Otherwise the pillar system will filter out the next change of direction.

8. **The labeling test supports primary-plus-secondary labels, not exclusive bins. Confidence: high.**

   | Incoming item | Primary | Secondary / qualification |
   |---|---|---|
   | Injection through retrieved memory | R8 | R3 for serving; R4 only if testing a classifier |
   | Signed versioned catalogue in a vector store | R1 | R7 only if it tests interchange or federation; signature is not availability |
   | Multi-agent shared-memory benchmark | R6 | `shared_state`; R2/R7/R8 according to the measured behavior |
   | Vendor “dreaming” during idle time | R2 | R6 for evaluation claims; mark vendor-origin and unverified |
   | Judge shares the judged system's failures | R6 | R4 if it evaluates an operational decision scorer |
   | MCP memory-server standard | R7 | R8 for scope/security semantics; proposal is not adoption |

**Rewritten pillar table**

| Id | Pillar | Thesis | What we believe today | What would change our mind |
|---|---|---|---|---|
| R1 | Evidence and reproducibility | Decisions need identifiable source evidence and an explicit replay guarantee. | Provenance and served-artifact/version records support audit; the cheapest sufficient preservation strategy is workload-dependent. | Mutation/replay experiments establish equivalent guarantees with less retained state or expose missing evidence. |
| R2 | State evolution and lifecycle | Updates, supersession, consolidation and retirement need distinct semantics. | Preserve correction history subject to explicit privacy/retention policy; mechanism benefits remain conditional. | Controlled lifecycle ablations change accuracy, recovery or cost enough to justify a specific mechanism. |
| R3 | Retrieval and context assembly | Select sufficient authorized evidence within a bounded budget. | Hybrid retrieval is a baseline; traversal, curation and stopping need task-specific evidence. | Matched-unit/budget tests reveal useful gains or unacceptable omission and latency. |
| R4 | Decision quality and abstention | Automate a decision only when its error costs and uncertainty are understood. | Rules first; learned scorers are optional and independently evaluated. | Held-out decision tests show a better risk/coverage/cost trade-off, including distribution shift. |
| R5 | Learning from experience | Outcomes may improve future behavior if attribution and transfer are valid. | Receipts and outcomes enable observation; reinforcement and induced procedures remain hypotheses. | Controlled reuse improves new task families without amplifying errors or bypassing policy. |
| R6 | Evaluation and research integrity | Conclusions require traceable protocols, independent checks and uncertainty. | Frozen artifacts and paired clustered analysis reduce—but do not eliminate—bias. | Audit challenges or external replication reveal blind spots and require revised protocols. |
| R7 | Interoperability and coordination contracts | Agents and stores need explicit, testable exchange and capability semantics. | Scoped interfaces, stable references and declared replay levels are a practical starting point. | Real backend/agent swaps fail or a simpler integration meets the same needs at lower cost. |
| R8 | Trust and governance | Evidence cannot authorize its own use, execution or promotion. | Identity, permissions, suppression, safe handling and review authority are system constraints. | Adversarial and recovery tests expose violations or validate a simpler control with equivalent guarantees. |

**Six-month regret:** the team would most regret letting engagement, repeated vendor claims and its own preferred theses become an automated consensus that looked like independent research.
 # Review: the agent research loop and Google Drive handoffs

**Date:** 26 September 2026. **Recommendation:** keep the separated fetch, digest, triage and hypothesis roles. Add an explicit evidence-to-experiment-to-belief chain, an independent challenge role and a small reliable handoff protocol. Google Drive is a reasonable artifact exchange for this pilot; correctness must come from the runners and artifact contracts.

This reviews the supplied handbook and pillar prompt. It does not assert that the described jobs, Drive folders or credentials have been inspected or deployed. Linked queue templates and the pipeline implementation were not supplied. [Pillar review](pillars-review-2026-09-26.md) contains the proposed eight-pillar taxonomy and evidence corrections.

## 1. The complete research loop

```text
External signals + adopter problems + previous experiment failures
    → source clusters
    → verified claims and counterclaims
    → trend/belief assessment
    → experiment proposal
    → independent challenge
    → prioritized, budgeted run specification
    → executor's result bundle
    → validated verdict
    → belief revision and next watch requests
```

Digest prose is a useful view of this chain. It should not be the sole source for a belief or a proposal. Every compression step needs links back to primary evidence so another agent can inspect what the previous agent omitted.

### Roles and ownership

| Role | Owns | Must not claim |
|---|---|---|
| Fetcher | Raw observations, query configuration/version, collection health | That popularity establishes truth |
| T0 triage | Clusters, verified claim notes, proposal candidates, watch answers | That an author-reported result is independently replicated |
| T5 hypothesis/portfolio agent | Mapping to beliefs, deduplication, experiment specification, queue decisions | That an accepted proposal has already run |
| Independent challenger | Source/attribution checks, alternatives, leakage and protocol review | That using another model guarantees independence |
| Experiment executor | Running the frozen specification, raw results, failures and resource usage | Authority to silently change the scorer or promote its result |
| Verdict/review role | Protocol compliance, statistics, confidence and disposition | A causal or production claim beyond the experiment |
| Delta/projector | Rebuilt indexes, weekly summaries, history mirror | A new authoritative decision merely through summarization |

These are responsibilities, not a requirement for seven continuously running agents. One scheduler can invoke bounded roles. Keep proposer, executor and final evaluator inputs/permissions separate where independence matters.

**The main missing contract is execution.** The handbook says T5 writes a verdict when a run closes, but does not say who launches it, where results arrive, or what proves it happened. Add `runs/` and `reviews/` before automating verdicts. T5 may publish a verdict only when it references a complete result bundle and the required review.

The fortnightly human register merge also means the present design is agent-assisted, not fully automatic. For greater autonomy, define a standing policy for permitted datasets, compute spend, concurrency and safe environments. Routine runs can proceed inside that policy; exceptions enter a review queue. Decide whether the repository register is authoritative or a derived mirror. Do not maintain two competing acceptance states.

## 2. Improve what the scraping and triage agents learn

### A. Separate popularity, novelty and evidential support

The fast-discard rule removes low-engagement posts and potentially important observations without links or numbers. That biases discovery toward established accounts and polished announcements.

- Use engagement to prioritize examination, not as the sole hard rejection rule.
- Reserve a bounded exploration sample of discarded/low-engagement items and audit how many relevant findings were missed.
- Deduplicate at **source and claim** level. Ten posts repeating one benchmark are one underlying result, not ten confirmations.
- Preserve the origin chain: post → paper/repository → specific claim/table → local note. Record shared authors, organizations, datasets and evaluation harnesses when judging independence.
- Add direct watches on primary repositories, papers and release notes, plus adopter incidents. This can be a separate intake adapter; the existing fetcher's logic need not expand.

### B. Verify the relevant part of a primary source

An abstract or README may identify a result without supporting its precise interpretation. For material numbers, inspect the corresponding table, methods and limitations. Record baseline, intervention, units, sample size, dataset, model, budget, uncertainty and evaluation method; use `unknown` when absent.

Replace the single paper-versus-repository hierarchy with a few evidence dimensions: directness, control quality, independence, reproducibility and applicability to our workload. A pinned implementation can settle an API claim better than a paper; a controlled experiment can settle an accuracy claim better than a README. Keep short source excerpts and locators rather than treating quoted numbers alone as validation.

### C. Define a trend object

Give the synthesis agent explicit fields:

`trend_id · time window · theme · claim_ids · independent source groups · observed volume · collection/query version · cap/coverage limits · counterevidence · maturity · affected belief_ids · proposed action`

Trend maturity could be `attention`, `implementation`, `controlled evidence`, `independent replication`, or `adoption`. An attention trend is useful market intelligence without being research confirmation.

Normalize comparisons for changes in tracked accounts, queries, collection windows and cap hits. “Mentions doubled” after doubling the watchlist is not evidence of acceleration. Report observed coverage limits instead of implying X is a representative census.

## 3. Make hypotheses a decision portfolio

Add a **belief register**, distinct from the topic taxonomy and discovery plan. Each entry needs an ID, current qualified statement, supporting/contradicting claim IDs, uncertainty, last review, linked experiments and the decision it affects. Update it through revision events. Generate the contradictions table from those events instead of waiting a month to capture corrections.

Each experiment card should specify:

- The decision it could change and why that decision matters now.
- Competing explanations and the simplest credible baseline.
- Frozen dataset, task-family split, scorer, code/configuration versions and expected artifacts.
- Primary metric, practical margin, uncertainty method and explicit positive/negative/**inconclusive** outcomes.
- Compute/money/time limits, dependencies, authorized executor and review requirements.
- Links to prior attempts; a rerun must identify a new condition or evidence rather than erase a failure.

Prioritize expected decision value relative to total execution/review cost, with an explicit exploration allowance. Use inspectable categories rather than a spurious precise LLM “value” score. Similar proposals should merge around one causal question even when they came from different pillars.

Replace **“at least three cards per week”** as a success target. A quiet week with no useful experiment can be correct. Track evidence quality, completed informative experiments, changed decisions, spend and queue age. Cap accepted work according to executor capacity; the handbook permits up to twelve cards per day without defining comparable execution throughput.

## 4. Fix these Drive handoff ambiguities first

| Handbook issue | Consequence | Minimal correction |
|---|---|---|
| Two daily runs each scan the last 24 hours | Repeated proposals; a missed run or deferred item can fall outside the window | Persistent consumed-source IDs/checkpoint plus a durable pending backlog; timestamps select discovery windows, not completion |
| `PC-YYYYMMDD-NN` and status-based filenames | Collisions across retries/runs; repeated status changes become ambiguous | Stable artifact/event IDs, unique run IDs and idempotency keys; filename is a readable label |
| “Newest file” determines state | Clock skew, late uploads or forks can silently reverse a decision | Decision events reference the predecessor and expected state; one decision writer, deterministic folding, conflicts surfaced |
| Append-only rule plus both agents replacing `index.json` | An undocumented exception and last-writer races | Immutable index snapshots with input watermark, generated by one projector; any mutable latest pointer is explicitly non-authoritative |
| Acceptance and experiment specification are separate uploads | A crash exposes an accepted proposal with no runnable specification | Upload/verify the specification first; acceptance references its ID/hash and consumers require complete dependencies |
| Notes live under `notes/`, but cards reference `evidence/sources/...` | Broken provenance outside a particular checkout | Logical artifact ID plus Drive file ID and hash; define the repository mirror mapping explicitly |
| Shared uploader credentials plus writer conventions | A role name alone does not enforce write ownership | Validate producer/schema/allowed destination at the uploader; restrict credentials where feasible; audit exceptions |
| Permanent parking/defer reasons lack retry rules | Important work can disappear silently | Retry-after, attempt count, blocked reason and age; alert on stalled items |
| Verdicts lack required run-artifact references | A plausible narrative can be mistaken for measured evidence | Result manifest, raw outputs and review references are prerequisites for a verdict |

Drive explicitly permits duplicate filenames, so use its file IDs and application-level artifact identity. [Drive file resource](https://developers.google.com/workspace/drive/api/reference/rest/v3/files)

For the pilot, paginated parent-folder scans plus processed IDs are sufficient. If volume warrants incremental polling, Drive offers a changes collection with saved page tokens; that feed reports file changes, so retain your own immutable decision events. Commit progress only after durable handling. [Drive change tracking](https://developers.google.com/workspace/drive/api/guides/manage-changes)

Handle transient failures with bounded retries and backoff, and recognize already-completed logical uploads. A timed-out upload must not produce a second experiment. [Drive error handling](https://developers.google.com/workspace/drive/api/guides/handle-errors)

Start with one runner per writing role and a non-overlap guard. If later multiple executors compete for jobs, introduce a coordinator that can atomically claim work; do not infer a distributed lock from the existence of a Drive filename.

### Minimal artifact envelope

```yaml
schema_version: 1
artifact_id: <stable logical ID>
artifact_type: proposal | decision | experiment | run_result | review | belief_revision
producer: <authorized role>
run_id: <unique invocation>
created_at: <UTC timestamp>
input_refs: [{artifact_id: <id>, file_id: <Drive ID>, sha256: <digest>}]
supersedes: <prior revision, if any>
idempotency_key: <stable logical operation>
```

An upload receipt records the output file ID and digest. A schema version permits evolution; hashes detect changed inputs; neither confers permission or proves truth. Keep the envelope small and use the existing readable Markdown/JSON payloads.

## 5. Protect the research loop from its own inputs

Posts, linked repositories and quoted instructions are untrusted evidence. They cannot authorize execution, alter the evaluator, request credentials or grant another agent permission. Preserve source text separately from the agent's interpretation. An experiment executor needs an approved run specification and bounded environment; a proposal card containing a shell command is insufficient authority.

Keep evaluation labels and final holdouts outside the proposer/optimizer's writable scope. Prefer executable checks where the task permits; sample model judgments against blinded independent review. Different model providers may diversify errors but do not establish independence by themselves.

For internal incidents and private research data, define where payloads may be sent and how access/retention changes propagate into derived cards, reports and mirrors. Append-only history should preserve accountable transitions without preventing required redaction or erasure.

## 6. Where I would join

**Proposed role: independent research challenger, then bounded experiment executor when explicitly assigned.**

Initial reads: candidate experiment, primary source notes and cited material, current belief, previous runs, frozen protocol and required budget.

Initial writes: immutable review in `reviews/`, targeted counterevidence requests in `watch/`, and suggested protocol corrections. Review outcomes: `ready`, `revise`, `insufficient_evidence`; these inform T5 rather than silently changing its decisions. Every review states what was actually checked and what remains unverified.

Trigger reviews for expensive experiments, changes to a central belief, novelty claims, contradictory sources and promotions. Add a small random sample of accepted and rejected cards to detect blind spots. This avoids making independent review a bottleneck for every low-impact item.

Later, a separately assigned execution role can produce a `runs/` result bundle. It should not independently certify its own result. No continuous Drive participation or scheduling is configured by this review.

## 7. Build order and acceptance exercise

1. **Define the contracts:** revised pillar labels, belief records, artifact IDs, valid status transitions and ownership. Add run results and independent review.
2. **Make the handoff reliable:** checkpoints, durable backlog, idempotent upload/consume, complete references, single-writer index and failure reporting.
3. **Run one complete experiment manually through those artifacts**, then automate the same path under a standing budget. Mirror history only after validating references.
4. **Improve discovery quality:** source independence, low-engagement sampling, direct primary watches and calibrated trend objects.

Acceptance exercise: a vendor posts an apparent improvement; two accounts repeat it; a primary source narrows the claim. T0 creates one evidence cluster with the correction. T5 specifies a baseline comparison. The reviewer detects a missing budget control. A revised, authorized run executes; its result is inconclusive. The belief stays qualified and the next watch request is recorded. Repeat with an upload timeout, duplicate scheduler invocation and a two-day outage: no extra run, no lost proposal, no fabricated verdict.

Weekly metrics should cover both **operations** (last successful run, backlog age, duplicate suppression, missing references, retries, budget) and **research quality** (claim corrections, independent evidence, missed-item audit, informative experiments, decision changes, replication failures). These tell you whether the company is becoming better informed rather than merely producing more files.

## Input identity

- `review-prompt-pillars.md`: SHA-256 `ab9b0cedcadba86934eb78f66dbc26c3644440e0cd01eb2b498392920501ebb9`.
- `t0-intelligence-handbook.md`: SHA-256 `44e86e475602a2ba71cf7c340762fe589b5eb74307ac85ea263d5f19044a1f5b`.
- Source files were read from `/Users/arunmenon/Desktop/`. Findings concern these versions and the proposed process, not a live audit of its implementation.
With this context, **the pillars are mostly right, but the research loop needs clearer responsibilities and evidence contracts.** The biggest gaps are experiment execution, independent review, and recording how results change your beliefs.

I saved two reviews:

- [Pillar review, including a rewritten table](/Users/arunmenon/Documents/ChatGPT/Engram/pillars-review-2026-09-26.md)
- [Agent research loop and Drive handoff review](/Users/arunmenon/Documents/ChatGPT/Engram/agent-research-loop-review-2026-09-26.md)

## 1. Adjust the pillars

Keep R1–R7, with three changes:

- **Add R8: Trust and governance**—permissions, poisoned evidence, execution authority, suppression, and review ownership.
- Rename R4 **Decision quality and abstention**, so it survives changes in vendors and models.
- Keep R5 **Learning from experience** as a research area, without assuming procedural memory is already the product.

Separate **topic labels** from **current beliefs**. An agent should classify a graph-retrieval paper under retrieval whether it supports or contradicts your preferred architecture.

Track multi-agent coordination and cost across the pillars.

## 2. Complete the research loop

The intended flow should be:

**Signal → verified claim → hypothesis → challenged protocol → experiment → validated verdict → belief revision**

The handbook covers intake and proposals well. It needs:

| Addition | Purpose |
|---|---|
| **Claim/source tracking** | Ten posts repeating one benchmark count as one result. |
| **Belief register** | Records what you currently believe, why, and which experiment could change it. |
| **Experiment executor contract** | Defines who runs an accepted experiment and which raw artifacts prove completion. |
| **Independent challenge** | Checks attribution, baselines, leakage and alternative explanations before expensive runs. |
| **Verdict requirements** | Prevents a persuasive summary from becoming a conclusion without results. |

Measure **informative experiments and decisions changed**, rather than requiring a minimum number of proposal cards.

## 3. Keep Drive, strengthen the handoffs

Drive is reasonable for this pilot. Fix these ambiguities first:

- Two daily scans of the last 24 hours need deduplication and a durable backlog.
- Give artifacts stable IDs; Drive filenames are not necessarily unique. [Google documentation](https://developers.google.com/workspace/drive/api/reference/rest/v3/files)
- Give the derived index one writer.
- Publish an experiment specification before a decision references it.
- Require verdicts to reference result bundles and reviews.
- Define recovery after retries, missed runs and partial uploads.

## 4. Where I would join

My initial role should be **independent research challenger**: inspect selected proposals and their primary evidence, identify weak claims, and return a review plus targeted watch requests.

Later, I could execute explicitly assigned experiments under a frozen protocol and budget, with another role reviewing the result.

**First milestone:** run one proposal through the entire loop—including an inconclusive result and an interrupted upload—before adding more agents or increasing intake volume.
