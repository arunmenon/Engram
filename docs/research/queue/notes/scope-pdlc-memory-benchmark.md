---
schema_version: 1
artifact_id: N-SCOPE-20260928-01
artifact_type: note
producer: triage
run_id: survey-20260928T071753Z-2e00
created_at: 2026-09-28T07:21:15Z
idempotency_key: note:scope:pdlc-memory-benchmark
input_refs: []
supersedes: null
pillar_primary: R6
pillar_secondary: [R10, R9]
memory_stage: evaluation
priority: 4
strength: opinion
beliefs_affected:
  supports: [B19, B20]
  contradicts: []
  note: design scope, no measurement yet; it would give B8 (graph lift only on typed questions) and B3 (supersession) a test on our own work
---

# Scope: our own memory test for product-development work (PDLC memory benchmark, v1)

Every public test of AI memory today asks about chat conversations or office tasks. None asks the questions an engineering team actually asks its memory: why did we pick this design, has this requirement changed, which pull request delivered it, did we already try this fix, is this note still true. We cannot tell customers that Engram's memory helps software teams more than Mem0, Zep or Letta until we measure exactly that. This note scopes a first version: six kinds of question, about 480 items drawn from our own history and from public projects, eight systems compared, roughly eight weeks and a few thousand dollars of model spend, plus a clear rule for dropping the effort if it tells us nothing the public tests do not.

- **URL:** internal design scope (no single source); sources cited per row below
- **Type:** design scope
- **Author / org:** triage agent, survey run survey-20260928T071753Z-2e00
- **Date:** 2026-09-28
- **Retrieved:** 2026-09-28 (primary pages re-fetched this run are listed in the checkpoint)
- **Cited by evidence:** priorities.md priority 4 (CTO decision 2026-09-28); pdlc-memory-layer.md section 6; discovery-plan.md H7, H10, P3
- **Relevance to a memory stack:** high. Without it, every graph, supersession and System One decision in the PDLC layer is judged on chat-memory data that does not contain the questions the layer exists to answer.

## TL;DR

- The public memory tests are either chat recall (LongMemEval, LoCoMo), office-task actions on synthetic personas (DolphinBench), stateful learning with a small software slice (CL-Bench), or multi-session coding with executable oracles (DreamBench-SWE). None scores decision rationale, requirement supersession, trace links, repeat-failure warnings or stale-memory detection on real engineering history.
- LoCoMo is near saturation and has a measured 6.4 % wrong answer key plus a lenient grader; its standard harness drops the abstention questions. Self-reported LongMemEval scores cluster at 89 to 95 %. Both are weak at separating the systems we care about.
- Proposed v1: six task families (decision-and-reason, requirement change, PR-to-requirement link, repeat-failure warning, stale memory, abstention), 360 scored questions plus 120 benign control items, half from our own repository history and half from public spec-driven repositories (SpecMine's Kiro and PR layers).
- Gold answers come from artifact structure (closing keywords, typed references, reverts, content hashes) and are human-verified; every item must pass a with-memory / without-memory validity filter (DolphinBench's rule).
- Systems: Engram, Mem0 OSS, Zep (Graphiti OSS), Letta, Hindsight, supermemory (hosted, if terms allow), no memory, full context. Report quality, cost per query and p50/p95 latency per family, and swap the decider at one memory stage at a time to compare System One models with LLMs.
- Kill: if system rankings on our items agree with rankings on LongMemEval and DolphinBench (Kendall tau at least 0.8 over the systems, family gaps inside the noise floor), our benchmark adds nothing and we stop at v1.

## What existing benchmarks measure and miss

Verification column: "fetched" means the arXiv abstract or primary page was fetched this run; "bus note" means the numbers come from a note already on the bus that read the full text; "landscape only" means taken from `context/memory-research-landscape.md` and not re-checked.

| Benchmark | What it tests | Data source | Size | Engineering / PDLC work? | Leakage, saturation, known problems | Verification |
|---|---|---|---|---|---|---|
| **LongMemEval** (Wu et al., arXiv 2410.10813, Oct 2024) | Information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention over user-assistant chat | Synthetic chat histories built around curated questions; scalable haystacks (S about 115k tokens, M about 1.5M tokens: inference from common usage, not re-read) | 500 questions | No. Personal-assistant chat | Self-reported vendor scores 89.6 to 95.6 % (Mem0 v3 94.4, Agent Zero 95.6, Hindsight 91.4; landscape 3.13) so top systems are near the ceiling; re-answer flip rate about 1 % (5/475, HivemindOS receipts) sets a noise floor; GPT-4o judge | fetched; bus note N-20260928-09 |
| **LongMemEval-V2** (Wu et al., arXiv 2605.12493, May 2026) | Static state recall, dynamic state tracking, workflow knowledge, environment gotchas, premise awareness over agent trajectories | Agent trajectories in "specialized web environments" | 451 questions; histories up to 500 trajectories and 115M tokens | Partly: agent work, workflow knowledge; web tasks, not product lifecycle | Work in progress; best reported 72.5 % (AgentRunbook-C), so not saturated | fetched |
| **LoCoMo** (Maharana et al., arXiv 2402.17753, Feb 2024) | QA (single-hop, multi-hop, temporal, open-domain, adversarial), event summarisation, multimodal dialogue | Machine-human pipeline: persona agents with temporal event graphs, human-edited | 10 conversations, about 300 turns and 9k tokens each, up to 35 sessions; about 1,980 QA (inferred from 446 adversarial = 22.5 %, D'Erme), of which the audit covered 1,540 | No | Audit (Penfield Labs, 2026-04-08): 99 of 1,540 answer keys wrong (6.4 %), GPT-4o-mini judge accepts 62.8 % of deliberately wrong but on-topic answers, honest ceiling about 93 to 94 %; the widely used harness evaluates categories 1 to 4 only, dropping 446 adversarial (abstain) questions, and its prompt forbids "not specified" (D'Erme, dev.to; date on page not reliable). Self-reported tops 92 to 94 %: saturated. Nous (arXiv 2606.22030) notes it has few contradictions | fetched (paper, audit, abstention post) |
| **DolphinBench** (Rathi, Yadav, Singh / Mem0, arXiv 2609.24971, Sep 2026) | Actions taken from long-term memory via MCP tools (email, Slack, Discord, calendar, CRM); accuracy, total cost, median latency | 3 synthetic knowledge-work personas, about 500k tokens each, Jan 2023 to Dec 2027 | 600 tasks (200 per persona) | No. Office knowledge work | Vendor-built (Mem0 is compared); one run per cell, no intervals; LLM judge from the same family as one agent model. Strength: each task validated as passing with history and failing without it. Vendor order flips by agent model | fetched; bus note N-20260926-05 |
| **CL-Bench** (Asawa et al., arXiv 2606.05661, Jun 2026) | Gain of a stateful system over its own stateless run on sequences with learnable latent structure | Six domains incl. "Codebase Adaptation" (sequential bug fixes from jazzband/tablib, 9 issues, and jd/tenacity, 10 issues) | 20 to 120 instances per sequence, 5 rollouts | Partly: 19 bug-fix issues. No requirements, designs or decisions | Programmatic rewards, no LLM judge; 95 % CIs. Finding: full history in context (ICL) beats memory modules; "memory modules introduce spurious generalizations and stale beliefs". Public repos: pretraining contamination possible (inference) | fetched; bus note N-SURVEY-20260927-06 |
| **DreamBench-SWE** (Singh, arXiv 2608.20664, Aug 2026) | Multi-session memory hygiene for software agents: later tasks depend on evidence from earlier sessions | Public benchmark release v2.1.0 on GitHub | 60 three-session sequences, 180 oracle checks | Yes, coding. Not requirements, decisions or trace links | Single author. No memory 21/180, verbatim event memory 82/180, one Mem0 config 97/180 | fetched |
| **MemoryAgentBench** (Hu, Wang, McAuley, arXiv 2507.05257, Jul 2025, rev. Jun 2026) | Accurate retrieval, test-time learning, long-range understanding, selective forgetting in incremental multi-turn form | Existing long-context datasets rewritten as multi-turn chats, plus new sets | not stated in the abstract | No | Reuses public long-context data, so contamination risk (inference) | fetched |
| **SWE-EVO** (Le et al., arXiv 2512.18470, rev. May 2026) | Long-horizon codebase evolution from release notes; multi-file changes validated by tests | Release notes of 7 mature Python projects | 48 tasks, about 21 files and 874 tests per task | Yes, but a single long task; not memory across sessions | GPT-4-class 25 % vs 72.8 % on SWE-bench Verified; public repos, contamination possible (inference) | fetched |
| **MOOSEDev question set** (Adam, arXiv 2608.13662, Aug 2026) | Supersession, set-completeness and negation questions over typed project memory | Neutral public corpus of 835 typed records, plus the author's own commit history and a live trial | 835 records | Yes: exactly our question classes | Author's own system vs a top-k vector store only (not SQL or hybrid); structured 0.98 to 1.00 vs vector 6 to 27 % | fetched |
| **ProjectMem** (Malo, Qiu, arXiv 2606.12329, Jun 2026) | Not a benchmark: self-study of a pre-action gate that warns before a repeated failed fix | 10 projects, 207 logged events, two months | 207 events | Yes | No metrics for the gate in the abstract; self-study | fetched |
| **CrossMeet** (with EvoWiki, arXiv 2608.23265, Aug 2026) | Decisions and risks revised across meetings; traceable QA | Meeting transcripts (six datasets) | not stated in the note | Near: project decisions over time | Overwrite protocol ablation -8.63 pp; judge differs from readers (kappa about 0.9) | bus note N-SURVEY-20260928-15 only |
| **SpecMine** (arXiv 2608.25202) | Not a benchmark: corpus of spec-driven development artifacts | 470,795 spec files in 73,030 repos; Kiro layout 98,574 files in 12,910 repos; 5,992 spec-touching PRs in 581 repos; 2.42M typed references | 14.7 GB, CC BY 4.0 | Yes: requirement, design, task, PR chains with commit history | Public, so any item built from it is exposed to future training (inference) | bus note N-SURVEY-20260928-13 only |

**What all of them miss.** No benchmark in this table asks (a) why a design decision was made, graded against the recorded reason, (b) whether an older requirement statement has been superseded, (c) which pull request implements which requirement with a plausible wrong candidate on offer, (d) whether a proposed fix already failed, (e) whether a stored claim still holds after the code under it changed, or (f) all of these on real engineering history with a private split. The landscape's own summary holds: "No published benchmark scores provenance correctness directly" (landscape 3.13). MOOSEDev comes closest on (b) but is one author, one system, and compares against vector top-k only.

## Task families for a PDLC memory benchmark

Each item is a question or a proposed action, asked of the agent after the memory system has ingested the history up to a cutoff time `t_q`. Every item carries: `family`, `t_q`, `question` or `proposed_action`, `gold` (typed), `gold_evidence` (artifact ids plus content hashes), `distractors`, `source_repo`, `split` (public / private-test).

### F1. Decision and reason, weeks later
- **Example.** History contains a design doc (week 1) choosing Redis Streams over Kafka "because the team runs a single region and needs consumer-group replay under 50 ms", a later chat thread restating it, and 3,000 unrelated events. At week 6: "Why does the ingest path use Redis Streams and not Kafka?"
- **Gold.** Decision (Redis Streams), the recorded reason(s) as a list of atomic facts, the anchor (doc id, section, hash).
- **Scoring.** Decision exact match (deterministic). Reason: fact-level coverage against the atomic list, graded by a rubric judge from a different model family than every reader; the judge is audited per release with deliberately wrong but on-topic answers (the LoCoMo audit found a 62.8 % false-accept rate), and its false-accept rate is reported. Citation correct if it names the anchored artifact. Unsupported reasons (hallucinated) are counted separately.

### F2. Requirement changed, older statements superseded
- **Example.** REQ-12 v1 (week 2): "Exports must be CSV." Ticket comment week 4: "Customer wants Parquet; CSV dropped." Spec commit week 5 rewrites REQ-12. Question at week 7: "What format must exports use, and has that changed?"
- **Gold.** Current value (Parquet), superseded value (CSV), the superseding artifact and date.
- **Scoring.** Current value exact match; "mentions change" binary; a hard error when the system asserts the superseded value as current (the costly failure, reported on its own). Negative variant: a requirement that was discussed but never changed, so asserting a change is an error.

### F3. Link a pull request to the requirement it implements
- **Example.** PR #214 "Add retry budget to webhook sender". Candidates: REQ-31 "Webhook delivery retries with backoff, max 5" (true), REQ-33 "Outbound email retries" (plausible wrong: same words, different component), REQ-29 "Webhook signing" (same component, wrong behaviour). "Which requirement does PR #214 implement? Say none if none."
- **Gold.** From closing keywords, spec task references and SpecMine typed references, human-verified; items where the automatic link and the human disagree are adjudicated or dropped.
- **Scoring.** Top-1 link accuracy; wrong-link rate on the planted hard negative (reported separately, since a wrong trace link is worse than none); "none" accuracy on PRs with no requirement (refactors). If the system gives a confidence, report reliability by band (inference: useful for the R9 comparison, see Metrics).

### F4. Warn before repeating a fix that failed
- **Example.** Week 3: attempt "raise the connection pool to 200" on issue #88; CI red; reverted with note "pool exhaustion was a leak in the retry loop, not size". Week 8, new session: proposed action "Increase DB pool size to 250 to fix timeouts on /export." Expected: warn, cite the week 3 attempt and revert.
- **Gold.** From revert commits, reopened issues, failed CI linked to a PR, closed-unmerged PRs with a stated reason; human check that the new action is materially the same fix.
- **Scoring.** Hazard items: warn rate with correct citation. Benign control items (a similar-looking action that did not fail before, or failed for an unrelated reason): false-warn rate. The false-warn rate needs enough benign cases to bound it; zero false warns in 60 cases bounds it at about 5 % (B21), which is v1's claim limit.

### F5. Spot a stale memory after the code changed
- **Example.** Memory (week 2): "Rate limiting is enforced in `gateway/middleware.py`, 100 req/min per key." Week 5 commit moves it to `edge/limits.go` and changes it to per-tenant. Question at week 6 or a pre-served briefing check: "Where is rate limiting enforced and at what limit?" plus "Is the stored note still true?"
- **Gold.** The anchored file and hash at the memory's write time vs at `t_q`; stale when the anchor's content changed in a way that falsifies the claim (human-labelled; a mere reformat is labelled still-true, giving hard negatives).
- **Scoring.** Stale-flag precision and recall (fit any threshold on one half, report on the other, as H10 requires); answer correctness on the current fact; a hard error when the stale claim is served as current. Controls: memories whose anchor changed harmlessly.

### F6. Abstain when memory has nothing
- **Example.** "What was the reason we rejected GraphQL for the public API?" when GraphQL was never discussed; or a question about a requirement id that does not exist; or a question whose answer is only after `t_q`.
- **Gold.** Abstain, generated by perturbing real F1 to F3 items (swap entity, shift date past `t_q`) and human-checked.
- **Scoring.** Abstain rate on unanswerable items and false-abstain rate on the paired answerable items, reported together (neither alone is meaningful). The harness never forbids "not stated", unlike the LoCoMo harness.

Optional v2 families (not in v1): set-completeness ("which requirements have no test?", MOOSEDev), constraint scope ("what constraints apply to ticket X?"), resume-a-task briefing quality.

## Data

**Sources.**
1. **Dogfood (private split).** Our own repository history, issues, pull requests, design docs and ADRs, and agent session transcripts. The task statement names this as the dogfood corpus in the programme plan; the programme plan itself was not in this run's inputs, so its exact scope (which repos, which date range, whether transcripts are retained) is an open question below. This split is never published and is the only split used for claims about Engram.
2. **Public (published split).** Repositories with linked issues and PRs, sampled from SpecMine's Kiro layer (requirements / design / tasks per spec with full commit history) and its PR layer (5,992 spec-touching PRs in 581 repos with at least 10 stars). Prefer repos whose spec history starts after the answer models' training cutoffs. Also reusable: CL-Bench's tablib and tenacity sequences for F4-style items (inference: needs checking that the failed attempts are visible in their history).

**Building a history.** For each source repo, replay events in time order into each memory system: issue events, PR open / review / merge, commits with diffs trimmed to changed hunks, doc revisions with content hashes, CI results, and (dogfood only) session transcripts. Each item has a cutoff `t_q`; the system sees only events before it. Distractor spacing follows DolphinBench: at least several hundred unrelated events between the evidence and the question where the history allows.

**Gold answers.**
- Draft gold is derived mechanically from structure: closing keywords and typed references for F3; spec diffs for F2; reverts, reopened issues, red CI and closed-unmerged PRs for F4; anchor hash changes for F5; perturbation for F6. F1 reasons are extracted from design docs and ADRs by an LLM as candidate atomic facts with quotes.
- Two annotators verify every item against the quoted evidence; 30 % are double-labelled blind, with Cohen's kappa reported per family and disagreements adjudicated. Items whose evidence cannot be quoted are dropped.
- Validity filter (DolphinBench): run a strong reader with the gold evidence and without any history, twice each; keep the item only if both with-evidence runs pass and both without-history runs fail. This removes items answerable from priors or from the code alone. Track the rejection rate per family; a high rate on public repos is a contamination signal.

**Leakage and contamination controls.**
- Label leakage (our B19 lesson): the query text never contains gold node ids or artifact ids; retrieval runs on the question text only; the scorer is frozen and imported, not reimplemented per system; the private test split is never used to tune Engram (discovery-plan ground rules).
- Training contamination: public items come from post-cutoff history where possible; the without-history arm of the validity filter catches memorised answers; a canary string is embedded in published files; a perturbation check (rename entities and ids consistently, re-ask) flags items whose accuracy drops only under renaming.
- Vendor overfitting: publish the public split and the harness, keep the private split and a rotating fresh split held back; report both, and treat a large public-minus-private gap as overfitting.
- Receipts: every answer is stored with the exact context the memory served and its sha256, and a tally script recomputes every score from files (HivemindOS receipts pattern), so third parties can audit without rerunning.

**Freshness.** Quarterly refresh: new items from the last quarter's dogfood history and from newly active public repos, with the oldest public items retired to an "archive" split that stays scorable. Each release is versioned and pinned (repo commits, model versions, judge prompt). The judge audit (deliberately wrong answers) reruns each release.

## Metrics

Per family, per system, with paired, family-clustered 95 % intervals and a predeclared practical margin (discovery-plan statistics rules). Noise floor: each system run at least three times on the unchanged set; report the flip rate.

| Family | Primary metric | Error metrics reported separately | Grading |
|---|---|---|---|
| F1 decision and reason | decision exact match; reason fact coverage | unsupported-reason rate; wrong citation | deterministic + audited rubric judge |
| F2 requirement change | current-value accuracy | superseded-value-as-current rate; false-change rate | deterministic |
| F3 PR link | top-1 link accuracy | hard-negative wrong-link rate; "none" accuracy | deterministic |
| F4 repeat failure | warn-with-citation rate on hazards | false-warn rate on benign controls | deterministic |
| F5 stale memory | stale-flag precision and recall at a fitted threshold | stale-served-as-current rate | deterministic + human labels |
| F6 abstention | abstain rate on unanswerable | false-abstain rate on paired answerable | deterministic |

**Cost and latency per query**, for every cell: memory-system cost (ingestion amortised over the items that use a history, plus per-query retrieval) and reader cost, in USD at list prices on the run date; tokens served to the reader; p50 and p95 latency end to end and for the memory call alone. Headline view is a quality-versus-cost frontier per family (DolphinBench's reporting rule), and CL-Bench's "gain over the same reader with no memory" as the "did memory help" number.

**System One models versus LLMs at each memory stage.** Hold the rest of Engram fixed and swap the decider at one stage at a time (one attributable change per run):

| Stage | Decision made | Families that expose it | Deciders compared | Stage-level metric |
|---|---|---|---|---|
| ingestion | which artifact type and node a record becomes | all (indirect) | LLM extractor; Jev typed extraction; open-weight (Laya, Intern-Decision) | typing accuracy on a labelled 200-record sample |
| linking | IMPLEMENTS / SUPERSEDES edge and confidence | F2, F3 | LLM; Jev; open-weight; rules (closing keywords only) | edge accuracy, hard-negative rate, reliability by confidence band |
| recall_gate | answer or abstain | F6 | LLM self-judgement; Jev Noul "evidence sufficient"; threshold on retrieval score | abstain / false-abstain pair |
| reranking | order candidates | F1, F3 | LLM listwise; Jev choice; cross-encoder | answer accuracy at equal served tokens |
| staleness | still true given current snapshot | F5 | LLM; Jev Noul; hash-change rule alone | stale-flag precision / recall vs the hash-change rule |
| routing (pre-action) | warn or not before an action | F4 | LLM; Jev; exact-match on lesson store | warn rate / false-warn rate |

For each stage report quality, cost per 1,000 decisions, p50/p95 decision latency, and whether memory text left our infrastructure (hosted vs self-hosted). A System One decider "wins" a stage only if end-task quality is non-inferior within the margin and cost or latency is materially lower, or quality is better (R9 thesis).

## Systems to compare

| System | How it runs | Notes |
|---|---|---|
| Engram | self-hosted, current main plus PDLC node types if ready | blocked by P1 to P3 (bulk-ingest payload loss, tenant id, harness replacement); run ledger-only and graph configurations as two rows |
| Mem0 | OSS SDK self-hosted; hosted platform as a second row if budget allows | OSS removed external graph stores (landscape 4.1), so graph memory is hosted-only |
| Zep | Graphiti OSS self-hosted | Zep Cloud optional |
| Letta | OSS server | git-backed context repositories (landscape 4.3) |
| Hindsight | OSS (vectorize-io) | already in DolphinBench and LongMemEval tables, useful for rank comparison |
| supermemory | hosted API | include only if terms permit benchmarking and publishing; DolphinBench showed high memory cost |
| No memory | reader only, current repo snapshot available | floor; the "gain" denominator |
| Full context | whole history up to `t_q` in the reader's window, truncated oldest-first when it exceeds the window | the CL-Bench lesson: this often wins; its cost is the price every memory system must beat |

Same reader model and prompt for every row; a second reader from another family as a robustness row. Vendor configurations: defaults, plus one documented tuning pass per vendor offered to each vendor before publication.

## Size, cost and timeline for v1

**Size.** 6 families x 60 scored items = 360, plus 120 benign controls (60 for F4, 60 for F5) = 480 items. Split: 240 dogfood (private), 240 public. Per-family n = 60 detects a gap of roughly 20 points between two systems at 80 % power with paired items (inference, depends on discordance); smaller gaps need v2 sizes. False-warn and false-abstain claims are limited to "below about 5 %" at this size (B21).

**Cost (inference, rough, at list prices).**
- People: one engineer 8 weeks (harness, adapters, replay); annotation about 480 items x 15 minutes plus 30 % double labelling, about 160 annotator hours.
- Model spend: ingestion of about 12 histories (4 dogfood, 8 public) into 6 memory systems; 480 items x 8 systems x 3 runs = 11,520 reader calls; full-context rows dominate (long prompts). Estimate USD 3,000 to 8,000 including judge and validity-filter runs, with full context taking over half.
- Hosted services: supermemory and Mem0 platform fees if included.

**Timeline (8 weeks, after P1 to P3).**
| Week | Work |
|---|---|
| 1 | freeze histories, event replay format, pick public repos from SpecMine |
| 2 to 3 | mechanical gold drafts, annotation, double labelling |
| 4 | validity filter, perturbation check, lock private split and scorer |
| 5 | adapters for each system, noise-floor runs |
| 6 to 7 | full runs, stage-swap runs for the System One comparison |
| 8 | analysis, kill-criterion check, write-up |

**What makes it credible enough to publish.**
- Pre-registration: hypotheses, metrics, margins and the analysis script committed and hashed before any system is run.
- Public split, harness and receipts released; private split scored by us for anyone who submits a system configuration.
- Independence: at least one external party (a design partner or academic group) reruns the public split and reproduces our numbers within the noise floor; Engram not tuned on the private split; vendors offered a configuration pass.
- Paired statistics with intervals, the judge audit, per-family kappa, and cost and latency next to every score.
- A result that is not flattering to Engram published as run (HivemindOS precedent of publishing a failed pre-registered run).

## Limitations, caveats, counter-evidence

- The dogfood history is one team's work; items may reflect our conventions. The public split is the check.
- Gold derived from closing keywords under-counts real links and over-counts sloppy ones; human verification catches some, not all.
- Full context may simply win (CL-Bench); if so, that is a finding, not a failure of the benchmark.
- DreamBench-SWE and MOOSEDev already cover parts of F4 and F2; we should reuse their items where licences allow rather than rebuild them (inference).
- Several sources in the table are single-author or vendor-authored; their numbers are cited, not endorsed.

## Takeaways

- Adopt now, regardless of v1: DolphinBench's with/without-history validity filter, per-query cost and latency reporting, the LoCoMo audit's wrong-answer judge test, and receipts with hashes.
- Build F2, F3 and F5 first: they need little human writing, their gold comes from structure, and they test the PDLC layer's core claims (H7, H10).
- Treat F1 as the expensive family (reason grading) and keep its judge audited.

## Open questions for the CTO

1. Which repositories and date range count as the dogfood corpus, and may session transcripts be used (privacy, retention, customer data in them)?
2. Will we publish the public split and results under our name, including results where Engram loses?
3. Is supermemory in scope given hosted-only operation and its terms on benchmarking?
4. Do we wait for P1 to P3 fixes before any Engram run, or run competitors first to validate the benchmark itself (recommended: run competitors first)?
5. Who is the independent reproducer: a design partner, an academic group, or none for v1?
6. Budget ceiling for full-context rows, which dominate spend?
7. Should v1 include the stage-swap System One comparison, or keep v1 to whole-system rows and run stage swaps as v1.1?

## Origin chain

priorities.md (priority 4, CTO 2026-09-28) -> pdlc-memory-layer.md sections 2, 4, 6 -> discovery-plan.md H7, H10, P3 and statistics rules -> bus notes N-20260926-05 (DolphinBench), N-SURVEY-20260927-06 (CL-Bench), N-20260928-09 (HivemindOS receipts), N-SURVEY-20260928-13 (SpecMine), N-SURVEY-20260928-15 (EvoWiki / CrossMeet) -> fetched this run: arXiv 2410.10813, 2402.17753, 2605.12493, 2609.24971, 2606.05661, 2608.20664, 2507.05257, 2512.18470, 2608.13662, 2606.12329, 2603.13258; Penfield Labs LoCoMo audit; D'Erme abstention post.
