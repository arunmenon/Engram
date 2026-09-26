# Beacon (agent-beacon): cross-harness session history with a Jev-scored, human-reviewed memory write gate

- **URL:** https://github.com/Asymptote-Labs/agent-beacon (docs: https://docs.beacon.sh)
- **Type:** repo
- **Author / org:** Asymptote Labs (asymptote-labs), MIT license
- **Date:** memory workflow added in CLI v1.3.17 (September 21, 2026); latest changelog entry read is v1.3.22 (September 23, 2026). Commit read: `df0b21b53f8393c60a6be1caf88eecaf86114ec5` (2026-09-25).
- **Retrieved:** 2026-09-26 (local copy: /private/tmp/claude-501/-Users-arunmenon-projects-localai-signals/3f9824a6-23ac-471e-adc7-a1ca0ec806fd/scratchpad/repos/agent-beacon, shallow clone)
- **Cited by evidence:** Decision models as the memory control plane / 2026-09-25 ethanwalkerman (quoting akshay_pachaar 2026-09-23: "uses Jev to identify the runs worth learning from"; "Beacon found 579 sessions across 5 coding-agent harnesses")
- **Relevance to a memory stack:** high. It is a concrete, readable implementation of a decision-model write gate (three yes/no Jev questions, a precondition plus a mean threshold) in front of a human review step, with provenance and supersession.

## TL;DR
- Beacon captures agent session traces from 20+ coding harnesses (Claude Code, Cursor, Codex, OpenCode, Cline, and others) into local JSONL, normalized to an OpenTelemetry-based event model.
- Memory is an explicit, opt-in loop: `beacon memory evaluations run` sends a bounded, redacted trace projection to TypeSafe Jev (`POST https://api.typesafe.ai/v1/systemone`, model `jev-latest`) with three `noul` (yes/no probability) questions.
- Gate: a trace becomes a *candidate* only if `task_success >= 0.50` AND the mean of the three probabilities `>= 0.60`. Jev returns no rationale, so Beacon writes no lesson text; a human (or an agent with the human) writes and approves the lesson.
- Approved memories live in a local SQLite `memory.db`, scoped per project, and are served back through read-only MCP tools (`search_memory`, `get_memory`, `get_memory_context`) or rendered as Agent Skills (`.agents/skills/<slug>/SKILL.md`).
- The social-post framing "keep what's reusable, drop the rest" overstates automation: nothing is written to memory without an explicit approve command. There is no decay, no update on read, and retrieval is plain substring AND matching ordered by recency.

## What it claims / describes
README positioning: "Beacon captures agent session history across Claude Code, Cursor, Codex, OpenCode, and 20+ other harnesses, then turns useful workflows, corrections, and debugging patterns into reusable knowledge for future agents." Loop shown in the README: Run agents -> Capture session history -> Evaluate what worked -> Extract useful knowledge -> Review + approve -> Reuse across future agents.

Capture layer (not memory, but the input): per-harness hooks, OTLP receivers and pollers write normalized events (sessions, prompts/responses, tool calls, commands, file activity, approvals, MCP interactions, token usage) to `~/.beacon/endpoint/logs/runtime.jsonl`. A rebuildable trace index sits over that log.

Memory layer (docs/concepts/cross-harness-memory.mdx, cli/beacon/internal/learning/):
1. Capture traces (hooks; these never call Jev).
2. `beacon memory evaluations run` on selected traces (filters: `--trace`, `--harness`, `--since`, `--until`, `--limit`). `--dry-run` previews selected traces and estimated cost with no network call.
3. Each trace is projected (bounded, redacted) and sent to Jev with three questions. Probabilities are stored as an *evaluation* with rubric version, rubric hash, evaluator endpoint/model and usage.
4. `PromotionDecision` turns a completed evaluation into a *candidate* if it passes the gate.
5. Reviewer runs `beacon memory candidates approve|reject|supersede`. Approve can replace title, body, applicability, kind and tags with reviewer-written text. Only approve creates a *memory*.
6. Reuse through `beacon mcp serve` (read-only tools) or `beacon memory skills preview|install`.

Docs are explicit: "This is deliberately review-gated. Jev probabilities help rank and classify traces; they do not automatically rewrite instructions, install skills, or execute actions."

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Candidate mean-score threshold | 0.60 | n/a | `CandidateScoreThreshold` in candidate.go | constant, not tuned in repo |
| task_success precondition | 0.50 | n/a | `CandidateTaskSuccessThreshold` | added after issue #649 |
| Example that slipped through before #649 | 0.27 / 0.86 / 0.69, mean 0.6067 | passed old mean-only gate | code comment in candidate.go | motivates precondition |
| Estimated Jev cost per trace | USD 0.00035 | n/a | `DefaultCostPerTrace`, overridable with `--jev-cost-per-trace` | estimate; real cost taken from `usage.cost_usd` if returned |
| Projection cap | 80 events, 1200 chars per text field | n/a | `maxProjectionEvents`, `maxProjectionText` | long traces keep first 40 + last 40 events |
| Jev request timeout | 10 s default | n/a | `--timeout` | |
| Response read cap | 2 MiB | n/a | `io.LimitReader(resp.Body, 2<<20)` | |
| `get_memory_context` max returned | 5 | n/a | MCP handler | |
| List limit | default 50, max 500 | n/a | `normalizeLimit` | CLI `--limit` default 25 |
| Sessions found in demo | 579 across 5 harnesses | n/a | akshay_pachaar post recording | from the X post, not the repo |
| Retrieval or memory quality benchmarks | not stated | | | the repo has no memory-quality evaluation |

## Mechanism details you could implement

**Rubric (cli/beacon/internal/learning/evaluator.go):**
```go
RubricVersion       = "beacon.learning.rubric.v1"
DefaultJevEndpoint  = "https://api.typesafe.ai/v1/systemone"
DefaultJevModel     = "jev-latest"
jevQuestionType = "noul"

{ID: "task_success", Prompt: "Did the trace complete the user's engineering task successfully?"},
{ID: "reusable_correction", Prompt: "Does the trace contain a correction or debugging pattern that future agents should reuse?"},
{ID: "evidence_supported", Prompt: "Is the reusable lesson supported by concrete events in the trace?"},
```
The rubric is hashed (`sha256` of the JSON question list) and there is a unique index on `(project_id, trace_id, rubric_hash)`, so changing the questions re-opens evaluation of the same trace.

**Jev request body built by Beacon** (one HTTP call per trace, all three questions in one call):
```json
{
  "model": "jev-latest",
  "state": { "trace": <Projection>, "rubric_version": "beacon.learning.rubric.v1", "rubric_hash": "sha256:..." },
  "questions": {
    "task_success": { "type": "noul", "instructions": "Did the trace complete ...?",
                      "criteria": { "true": "The trace satisfies this criterion.",
                                    "false": "The trace does not satisfy this criterion." } },
    "reusable_correction": { ... }, "evidence_supported": { ... }
  }
}
```
Headers: `Content-Type: application/json`, `Authorization: Bearer <key>`. Key from `--jev-api-key`, else `TYPESAFE_API_KEY`, else `BEACON_JEV_API_KEY`. Endpoint from `--jev-endpoint` / `BEACON_JEV_ENDPOINT`; model from `--jev-model` / `BEACON_JEV_MODEL`.

`Projection` fields: `trace_id`, `title`, `harness`, `repository`, `events[]` where each event has `number`, `type`, `action`, `title`, `summary`, `content` (content falls back to the command string). Every text field passes `CleanString(value, 1200, true)` which truncates then applies `RedactString` (secret-pattern redaction to `[REDACTED]`). Long traces keep head and tail:
```go
// Long sessions resolve at the end: keep the opening context and the tail
head := maxProjectionEvents / 2
tail := maxProjectionEvents - head
... Summary: fmt.Sprintf("%d events omitted from the middle of this trace", ...)
```

**Response parsing:** `answers` map keyed by question id; probability read from `noul`, else `probability`, else `score`; `confidence` also stored. Also accepts `model`, `usage` (with `cost_usd`), and legacy `questions`/`results`/`score`/`cost_estimate_usd` shapes from internal compatible evaluators. Probabilities are clamped to [0,1]. `evaluation.Score` = plain mean of the three probabilities (overridden by a top-level `score` if the server sends one).

**Write gate (candidate.go):**
```go
const CandidateScoreThreshold = 0.60
const CandidateTaskSuccessThreshold = 0.50
// The score is a mean, so two high answers about reusability and evidence
// could outvote a judge who said the task failed: 0.27/0.86/0.69 averages 0.6067
```
Order: status must be `completed`; `task_success` must be answered (missing answer fails); `task_success >= 0.50`; mean `>= 0.60`. Rejections carry a human-readable reason string.

**Candidate construction:** `kind` is chosen by keyword match on the trace title: "convention"/"standard" -> convention; "gotcha"/"pitfall" -> gotcha; "workflow"/"process" -> workflow; "fix"/"debug"/"fail" -> debugging_pattern; default correction. Body, when Jev gives no rationale: "The evaluator returned scores with no rationale, so no lesson text was extracted. Review the source trace before approving." plus the per-question probabilities. Tags: `beacon`, kind, harness name.

**Data model (store.go, SQLite `memory.db` beside the runtime log base dir, `PRAGMA user_version` schema versioning):**
- `evaluations(id, project_id, trace_id, status, created_at, updated_at, rubric_hash, evaluator, evaluation_json)`
- `candidates(id, project_id, state, kind, title, source_evaluation_id, memory_id, created_at, updated_at, candidate_json)`; states: candidate, approved, rejected, superseded.
- `memories(id, candidate_id, project_id, kind, title, created_at, updated_at, superseded_by, memory_json)`; unique on `candidate_id`.
- Memory kinds: `workflow`, `correction`, `debugging_pattern`, `gotcha`, `convention`.
- Each memory keeps `evidence[]` = `{trace_id, event_ids[], summary}` for provenance, plus `applicability` ("When a future agent in this project hits a similar workflow, regardless of harness.").
- Project id derived from git metadata of cwd (or `--project`). No automatic cross-project or user-global memory.

**Supersession (the only "forget" path):** `beacon memory candidates supersede <id> --replacement <memory-id>` sets `superseded_by` on the old memory; `ListMemories` filters `superseded_by IS NULL OR ''`. Replacement must be in the same project.

**Read path:** `ListMemories` selects non-superseded memories for the project `ORDER BY updated_at DESC`; with a query it applies `matchesText`, which lowercases and requires every whitespace-separated term to appear as a substring of id+title+body+kind. No embeddings, no BM25, no scoring. `get_memory_context` caps at 5 results. Reads do not modify memories (no access counts, no reinforcement).

**Lesson-writing guidance** (agent-skills/skills/beacon-memory-distill/references/lesson-quality.md), useful as an extraction prompt: title imperative under 80 chars naming the tool/file/error; applicability starts with "when", "before" or "after"; body 3 to 10 lines (what to do, why in one sentence from the trace, how to confirm); 2 to 4 tags; reason cites trace event numbers. "Not a memory": summaries of what happened, one-off facts, anything true only on one machine/branch/day, speculation not in the trace, restatements of repo docs. Check duplicates with `beacon memory list -q` before approving. The distill skill tells the agent: "Never approve a candidate with its placeholder body".

## Limitations, caveats, counter-evidence
- No metrics anywhere in the repo on precision of the Jev gate, lesson quality, or downstream agent improvement. The ethanwalkerman post also says "no metrics given".
- The thresholds (0.50, 0.60) are hand-set constants; no calibration study is included (inference: they assume Jev probabilities are calibrated).
- Jev gives probabilities only, so Beacon's gate decides *which traces to look at*, not *what to write*. Content extraction is human or agent authored. Calling it a write gate is accurate only in the sense of a candidate filter before human approval.
- The `kind` heuristic is keyword matching on the trace title, easily wrong (inference).
- Retrieval is naive substring AND matching with recency order; will not scale to large memory sets or paraphrased queries (inference).
- No decay, no update-on-read, no automatic consolidation or dedup (dedup is a manual check in the skill instructions).
- Only one trace per candidate (evidence list has one entry at creation); no cross-trace aggregation of repeated lessons (inference from `CandidateFromEvaluation`).
- Sending traces to hosted TypeSafe is an external data flow; mitigated by truncation plus regex redaction, and by an internal-endpoint option.

## Takeaways for tuning a memory stack
- Use a precondition plus aggregate pattern for multi-question gates: a hard floor on the "did it succeed" question, then a mean over the rest. Beacon's #649 fix shows a mean alone lets failed episodes through.
- Ask one decision-model call per episode with several typed yes/no questions in a single request, keyed by stable ids, and store the rubric hash with results so a rubric change triggers re-evaluation.
- When projecting long episodes for a scorer, keep head and tail rather than the first N events; the fix is usually at the end.
- Keep provenance (trace id + event ids) on every memory and a `superseded_by` pointer instead of deletes.
- If your decision model returns probabilities only, do not store scores as lesson text; route high-scoring episodes to an extraction step (LLM or human) and make that step cite evidence.
- The lesson-quality rubric (imperative title, "when/before/after" applicability, 3 to 10 line body, "not a memory" list) is a ready-made extraction prompt.

## Open questions
- How calibrated are Jev `noul` probabilities on agent traces, and what precision/recall does the 0.50 / 0.60 gate give on a labelled set? Not stated.
- What fraction of evaluated traces become candidates, and of those, how many are approved? Not stated (the 579-session demo gives no candidate counts).
- Does approved Beacon memory measurably improve later agent runs in another harness? Not stated.

---
