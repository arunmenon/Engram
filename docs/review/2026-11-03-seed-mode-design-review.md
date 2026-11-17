# Design review: explicit-only seed mode for artifact retrieval

Date: 2026-11-03. Branch `feature/engram-walkthrough` verified; the working tree has 484 uncommitted paths, and everything below was read from the working tree. Nothing was implemented, and no pack, expected answer or runtime data was changed. One reproduction script was run on the memory backend (section 2); no other tests were run.

## 1. Verdict: approve with changes

The diagnosis is correct and reproduced. A `seed_mode` option is the right shape: no existing capability suppresses text discovery, and the one-line alternative (skip word matching when seeds are given) changes default behaviour and leaves three other discovery paths open. Five changes are needed before implementation, in order of severity:

1. Strict mode must fail when a selection does not resolve, including the two silent drops that exist today (unknown label or absent node, and the graph-call budget), and when selections exceed `max_nodes`. Today all three degrade silently.
2. The completeness path must be shown by test to never reach the global scan in strict mode. With the rule in change 1 it cannot, but the guarantee rests on `_seeds` raising, not on `_completeness_scope`, so the test is the contract.
3. `EvalQuestion` is `extra="forbid"`, so the sandbox, the eval export, the assistant's journey authoring and the journey runner must gain the field in the same commit or they break.
4. Response metadata needs a distinct `seed_strategy` value and the eval report needs a per-question error field, so an empty strict answer is distinguishable from a failed one.
5. The option belongs to `ArtifactQuery` only. The generic `/v1/query` engine has its own seed fusion and is out of scope; the design should say so.

## 2. Observed behaviour

### Diagnosis confirmed

`ArtifactRetriever._seeds` (`src/context_graph/retrieval/artifacts.py:454-530`) resolves the given ids first, then runs key, pattern, number and word discovery over the question text, and returns `[*given, *ranked[:seed_limit]]` (line 530). Given seeds are excluded from each discovery pass (`match_ref in given_refs`), but discovered seeds are never excluded because a given seed exists.

Word discovery runs whenever precise discovery found nothing (`if words and not found`, line 516); a given seed does not count as "found". For "Which incidents affect US checkout?" the words after stop-word and type-word filtering are "affect" and "checkout". "checkout" matches the `name` field of both Service nodes; the US one is skipped as given, the EU one becomes a word seed.

Reproduced on the memory backend with the saved draft (`output/workbench/spanner/northstar-ui-result.json`, content and proposal pack unchanged):

```
QUERY 'Which incidents affect US checkout?' given ('Service:us|checkout',)
   seed Service:us|checkout origin given score 1.0
   seed Service:eu|checkout origin word  score 0.387
   -> nodes [Incident:eu|INC-1042, Incident:us|INC-1042, Incident:us|INC-1043, Service:eu|checkout, Service:us|checkout]
QUERY 'Which incidents affect EU checkout?' given ('Service:eu|checkout',)
   seed Service:eu|checkout origin given score 1.0
   seed Service:us|checkout origin word  score 0.387
mean_f1 0.65
```

Control: the same question with text "incidents for this service" (no word that matches a Service name) returns exactly `Incident:us|INC-1042` and `Incident:us|INC-1043`. The Spanner run recorded the same three-incident answers for both questions with mean F1 0.65 against 1.0 (`sandbox.evaluation` in the same file, `backend: spanner`, slot `engram-sandbox-01`, cleanup verified).

Scores do not help: traversal scores a reached node as `parent.score * weight / top` (line 724), so the EU incident carries 0.387 against 1.0, but evaluation is set F1 over node ids (`ontology/evaluation.py:141-184`), which ignores score.

### Other mechanisms that broaden results from the question text

All run before the given seeds are returned and all would be switched off by strict mode:

| Mechanism | Lines | Example that would broaden a Northstar-style question |
|---|---|---|
| Key tokens, searched over the type's text and key fields | 497, 544-582 | "status of INC-1042 for US checkout" seeds both accounts' INC-1042, because `search_nodes` matches the `id` field of each |
| Pack key patterns, exact lookup by last key field | 498, 584-612 | Any pack that declares a key pattern for a composite-key type seeds every node sharing the last key value |
| Integer references (`#7`, "PR 7") | 499-516 | Composite int keys: `Change:acme/app|7` and `Change:acme/api|7` |
| Word matching, rarity weighted | 516-518, 614-672 | The Northstar case |

Mechanisms strict mode does **not** affect, and the design should say so:

- Traversal reach. Depth, direction, edge weights and drift rules decide what a seed reaches. A US seed one hop from a node shared across accounts (a Merchant used by both services, say) reaches EU nodes at depth 2 regardless of seed mode.
- Intent inference. When `intent` is not given, it is classified from text (line 257). When the classified intent's pack is evaluation-pending, it is dropped (lines 258-264) and, if nothing remains, the query runs with every artifact intent's edges in both directions (lines 269-272). The route rejects an explicit pending intent with 409 but an inferred one silently widens. Out of scope here; worth a separate finding.
- Admission. An untrusted, uncorroborated given seed is kept even when `include_untrusted` is false (`_admit`, lines 851-855: only non-given nodes are deleted) and keeps `retrieval_reason: direct`. Existing behaviour, unchanged by seed mode, but strict mode makes the given seed the whole answer so the design should state it.

### Silent degradations that already exist and that strict mode must turn into errors

| Case | Lines | Today |
|---|---|---|
| Selection with an unknown type label, or missing `:rest` | 445-452, 458 | `_parse_node_id` returns None, the id is dropped, discovery proceeds |
| Selection whose node does not exist | 460-462 | `get_nodes` omits it, discovery proceeds; `meta.seed_nodes` silently lacks it |
| Graph-call budget already spent | 459, 318-324 | `_spend` returns False, **no** given seed is resolved, `truncated` is set, discovery also gets no calls; the answer is empty with `truncated: true` and nothing says why |
| More selections than `max_nodes` | 287 | `seeds[:max_nodes]` drops the rest; `truncated` is not set |
| Given seed resolves but its key property does not round-trip (`_ref(...) != ref`) | 462 | Dropped silently |

The journey runner already asserts on `first_seed` and `required_seeds` against `meta.seed_nodes` (`workbench/journey_runner.py:425-431, 496-498`), which is the right instinct; strict mode makes it a guarantee instead of a check.

### Where a query is built today

| Caller | File:line | Builds text | Passes seeds | Passes intent |
|---|---|---|---|---|
| API | `api/routes/artifacts.py:71-80` | request | request (max 50) | request, validated |
| Eval sets | `ontology/evaluation.py:165-171` | question | question | question |
| Workbench sandbox | `workbench/sandbox.py:30-46` via `evaluation_artifact` → `EvalSet` | question | question | question |
| Eval YAML export | `workbench/api.py:760` | same artifact | | |
| Journey runner, retrieval checks | `workbench/journey_runner.py:362-368` | `text` or `intent + " " + seed` | `seeds` or `[seed]` | check |
| Journey runner, evaluation checks | `journey_runner.py:337-345` → `EvalSet` | | | |
| Assistant-authored journeys | `workbench/journey_authoring.py:109, 185-205` | validated through `EvalSet`; examples carry `seed_node_ids` | | |
| Benchmark | `workbench/journey_benchmark.py:71` | text only | none | none |
| Work-budget wrapper | `journey_benchmark.py:114-139` | passes the query through | | |

PDLC fixtures: 35 retrieval checks, 34 with text, 5 with seeds, 4 with both text and seeds, 1 with a seed and synthesized text. Those four combine discovery with a selection today and must keep doing so under the default.

The frontend stores `seed_node_ids` and `intent` per question (`demo/frontend/src/workbench/types.ts:7-15`), edits seeds through "Starting point (optional)" and a raw "Seed node IDs" list (`Workbench.tsx:1522-1543, 1619-1628`), and has no test suite.

## 3. Findings, by severity

### F1 (blocker): strict mode has no error path and three silent fallbacks to define

`_seeds` cannot signal failure; it returns a list. In strict mode, every row in the "silent degradations" table above must raise. Without this, a strict query whose single selection does not exist on this graph returns an empty answer with `truncated: false`, indistinguishable from a valid question with no results, which is exactly the fallback the proposal forbids.

Failure example: eval question `seed_node_ids: ["Service:us|checkout "]` (trailing space from a paste). Today: id dropped, discovery seeds both services, F1 as now. With a naive strict implementation that just skips discovery: empty answer, F1 0, no indication that the selection was the problem.

Required: a typed error raised from `_seeds` (name it for what it carries, e.g. `UnresolvedSeedsError(unresolved=[...], reason="missing" | "unparseable" | "budget" | "over_capacity")`), caught by each caller (section 5).

### F2 (major): the completeness global scan is only one empty list away

`_completeness_scope` (lines 928-978) calls `_all_of`, a scan of every node of the subject type, whenever `result.nodes` is empty at line 974. In strict mode that happens if and only if no selection resolved. F1 closes the door, but nothing in `_completeness_scope` itself knows about seed mode. The design should add the guard where the scan is, not only upstream: in strict mode `_all_of` is never called, and an empty scope returns an empty candidate list with `retrieval_channels` reporting zero. A test must call a missing-links intent in strict mode with (a) valid seeds, asserting `find_nodes` is not called with an empty filter, and (b) an unresolvable seed, asserting the typed error.

### F3 (major): the strict `EvalQuestion` schema breaks every carrier unless changed together

`EvalQuestion` is `extra="forbid", strict=True` (`evaluation.py:63-70`). The sandbox builds an `EvalSet` from workbench questions (`sandbox.py:30-46, 143`), the eval YAML export dumps the same dict (`api.py:760`), the journey runner validates evaluation checks through `EvalSet` (`journey_runner.py:339`), and assistant-authored journeys are validated the same way (`journey_authoring.py:109`). Adding `seed_mode` to the workbench `Question` without adding it to `EvalQuestion` in the same change makes `run_sandbox` raise a validation error for every draft. Conversely, old YAML and old drafts without the field must still load, so the field needs a default of `discover` everywhere.

### F4 (major): response and report contracts cannot express "strict, valid, empty"

`QueryMeta.seed_strategy` is a free string, always `"artifact_seeds"` (line 1139). `QuestionResult` has `id, f1, found, expected` only. A strict question that legitimately returns nothing and one that failed to resolve both produce `found: []` and F1 0 unless the report carries the error. Required: `seed_strategy: "explicit_seeds"` in strict mode, `seed_nodes` equal to the resolved selection in the given order, and `QuestionResult.error: str | None` surfaced in `as_dict` and in the sandbox evaluation block. `QueryMeta` is frozen for signature changes but may gain fields with defaults; reusing `seed_strategy` avoids even that.

### F5 (minor): more selections than `max_nodes` is dropped silently in both modes

Line 287 cuts `seeds[:max_nodes]` without setting `truncated`. With `retrieval_max_seed_ids` at 50 and a caller passing `max_nodes: 10`, forty selections vanish. In strict mode this must be an error (over_capacity); in discover mode it should at least set `truncated`.

### F6 (minor): the option name and values

`explicit_only` describes the mechanism; the UI will say something like "Only start from the entities I selected". Either name works if the values are closed (`Literal["discover", "explicit"]`) and documented on `ArtifactQuery`, the route model, `EvalQuestion`, `Question` and `QueryOptions`. Avoid a boolean: a third mode (discover, but filter discovered seeds by a property) is the likely next request and a boolean would have to be renamed.

### F7 (minor, scope statement): `/v1/query` is a different engine

`RetrievalEngine.get_subgraph` (`retrieval/engine.py:244-265`) fuses keyword and vector seeds and then adds user seeds. The proposal's "shared engine" means the artifact retriever; the design should state that `seed_mode` does not apply to `SubgraphQuery`, so nobody expects `/v1/query` to honour it.

### F8 (note): setting strict mode on the Northstar questions is a content edit

The two reviewed questions have `reviewed: true`. The UI resets `reviewed` on any question edit (`Workbench.tsx:1536-1540`), so turning strict mode on will require re-ticking "I checked these answers". Expected answers are not touched. The README (`docs/examples/northstar-payments/README.md:53-55`) and the exercise record should be updated with the re-run result, not rewritten.

## 4. Smallest recommended implementation

Engine, one file plus one model field:

- `ArtifactQuery.seed_mode: Literal["discover", "explicit"] = "discover"` (`artifacts.py:135`).
- In `_seeds`: after resolving `given`, if `seed_mode == "explicit"`: require `query.seed_node_ids` non-empty; require every id to parse and resolve (compare the deduplicated parsed refs with `given`); require the budget call to have succeeded; require `len(given) <= query.max_nodes`; on any failure raise the typed error; otherwise `return given` before any text scan. Intent classification from text is untouched because it happens in `retrieve`, not `_seeds`.
- In `_completeness_scope`: `if seeds: ... elif query.seed_mode == "explicit": candidates = [] else: _all_of(...)`.
- In `_atlas`: `seed_strategy = "explicit_seeds" if query.seed_mode == "explicit" else "artifact_seeds"`.
- Line 287: set `result.truncated` when seeds are cut (discover mode).

Carriers, each a field with default `discover` and the error mapped:

- `api/routes/artifacts.py`: request field; 422 when `explicit` with empty `seed_node_ids` (static); catch the typed error and return 422 with `detail` and `unresolved_seed_ids` (it is a client-input problem on this graph, not a server fault; 404 would be read as "route missing").
- `ontology/evaluation.py`: `EvalQuestion.seed_mode`; `QuestionResult.error`; in `run_eval_set` catch the typed error per question, record `error`, F1 0, `found: []`. Document in the module docstring example.
- `workbench/models.py`: `Question.seed_mode`; `sandbox.evaluation_artifact` passes it through (which also fixes the YAML export at `api.py:760`).
- `workbench/journeys.py`: `QueryOptions.seed_mode` so journey retrieval checks can opt in via `query_options`; the runner catches the typed error and records a failed check with the reason rather than crashing the journey.
- `workbench/journey_authoring.py`: add `seed_mode` to the evaluation example so the assistant learns it exists; otherwise unchanged.
- Frontend: `Question.seed_mode` in `types.ts`; inside "Starting point (optional)" a checkbox "Only start from the entities I selected" enabled when at least one entity is selected, resetting `reviewed`; the report card shows the error sentence from `QuestionResult.error` ("Starting point Service:us|checkout does not exist on this graph") instead of a bare F1 0.

Not in scope: tenancy, account filters, traversal scoping, `/v1/query`.

## 5. Acceptance-test matrix

Unit, memory backend, `tests/unit/test_artifact_seed_mode.py` (new) plus small additions where noted. Each row is one test.

| # | Setup | Query | Assert |
|---|---|---|---|
| 1 | Northstar graph from `docs/examples/northstar-payments` (projected through the sandbox, as the repro did) | both questions, `explicit` | US returns exactly the two US incidents, EU exactly the EU one, mean F1 1.0; expected answers unchanged |
| 2 | same | both questions, `discover` (default) | mean F1 0.65, unchanged from today (pins the default) |
| 3 | PDLC graph used by `test_pdlc_retrieval_eval.py` | question text that would seed by key, pattern, number and word; one given seed; `explicit` | `search_nodes` and `find_nodes` are never called (count with the wrapper pattern from `retrieve_with_work_budget`); `meta.seed_nodes == given`; `seed_strategy == "explicit_seeds"` |
| 4 | any | `explicit`, `seed_node_ids=()` | typed error, reason empty selection |
| 5 | any | `explicit`, one id with unknown label; one with no `:rest` | typed error listing each unparseable id |
| 6 | any | `explicit`, one resolving id and one absent id | typed error listing only the absent id; no traversal performed (neighbors not called) |
| 7 | retriever with `max_graph_calls=0` | `explicit`, valid id | typed error, reason budget; `discover` on the same retriever returns empty with `truncated: true` (existing behaviour, now asserted) |
| 8 | any | `explicit`, 3 valid ids, `max_nodes=2` | typed error, reason over capacity; `discover` sets `truncated: true` |
| 9 | PDLC graph | `explicit`, several valid ids of mixed types, `trace` | `meta.seed_nodes` equals the ids in given order; result is the union of each seed's traversal (compare with per-seed runs) |
| 10 | node with `source_trust: untrusted`, uncorroborated | `explicit`, that node, `include_untrusted=False` | node is present with `retrieval_reason: direct` (documents existing admission; change the assertion if the design decides otherwise) |
| 11 | PDLC graph | missing-links intent, `explicit`, valid subject seed | `_all_of` not reached: `find_nodes` never called with an empty filter; scope derives from the seed; `retrieval_channels` populated |
| 12 | PDLC graph | missing-links intent, `explicit`, absent seed | typed error, not a global scan |
| 13 | PDLC graph | missing-links intent, `explicit`, valid seed with no subject descendants | valid empty answer: no error, `nodes == {}` or seeds only per existing behaviour, `truncated: false` |
| 14 | eval set YAML with `seed_mode: explicit` on one question and absent on another | `load_eval_set` | loads; absent defaults to `discover`; `seed_mode: strict` is rejected with a path in the message |
| 15 | eval set where one strict question has an absent seed | `run_eval_set` | that question has `error` set, F1 0; the other questions still run; `as_dict` carries `error` |
| 16 | route | `{"query": "x", "seed_mode": "explicit"}` with no ids | 422 before any graph read |
| 17 | route | `explicit` with an absent id | 422 with `unresolved_seed_ids`; `discover` with the same body is 200 |
| 18 | route | old body without `seed_mode` | 200, `seed_strategy == "artifact_seeds"` |
| 19 | workbench | `Content` with and without `Question.seed_mode`; `evaluation_artifact` → `EvalSet.model_validate` | round-trips both ways; exported YAML contains the field |
| 20 | workbench store | a draft saved before the field existed | loads with `discover` |
| 21 | journey runner | retrieval check with `query_options.seed_mode: explicit` and an absent seed | check fails with the error reason; journey completes |
| 22 | existing suites | `test_pdlc_retrieval_eval.py`, `test_resolved_artifact_seeds.py`, `test_artifact_route.py`, all PDLC journeys via the workbench runner | unchanged results |

Spanner: rows 1, 2, 6 and 11 repeated under the `integration` marker against the emulator, since `get_nodes`, `search_nodes` and `find_nodes` are adapter code and the memory backend cannot prove the Spanner paths. Row 1 is also the acceptance for the Northstar exercise: re-run the saved draft on a sandbox slot after turning strict mode on for both questions, and record the result next to `northstar-ui-result.json` without editing it.

## 6. Answers to the review questions

1. Diagnosis correct; reproduced. Other broadening paths: key tokens, key patterns, number references (all text-driven, all closed by strict mode); traversal reach, inferred-intent widening under evaluation-pending packs, and given-seed admission (not closed by strict mode).
2. No existing capability does this. The smallest engine change without an option, `if words and not found and not given`, fixes Northstar but alters the default for the four PDLC checks that mix text and seeds and leaves key, pattern and number discovery on. The option is the smallest coherent fix.
3. Precise with the rules in section 4: all selections resolve or the query fails; the answer is the union of each selection's traversal; selections beyond `max_nodes` are an error; trust admission is unchanged and must be stated; budget exhaustion before resolution is an error, after resolution it is `truncated: true` as today.
4. Yes, today: `_all_of` runs whenever no seed resolves. Closed by raising in `_seeds` and guarded again at the scan site (F2).
5. Section 4: request field, two 422 shapes, `seed_strategy`, `QuestionResult.error`, journey check failure reason.
6. Yes. The default leaves `_seeds` byte-for-byte on the current path; rows 2, 18 and 22 pin it.
7. Yes, once `EvalQuestion` carries the field (F3). The chain is `Question` → `evaluation_artifact` → `EvalSet` → `ArtifactQuery`; the same dict is exported as YAML and consumed by `run_gate` on a rebuild.
8. Section 5.
9. Anything that is not "start only here": "all open incidents in the US account" (no selection; needs a property filter on discovery or on candidates); answers that must exclude nodes reachable from a selection through a shared neighbour (traversal scope); any claim that an account cannot see another account's nodes (that is tenancy, and both accounts are one tenant here).

## 7. Uncertainties and what was not verified

- The Spanner adapter's `get_nodes`, `search_nodes` and `find_nodes` were not read; the matrix repeats the key rows there because of that.
- The frontend was read, not run; whether the question editor re-renders cleanly with a new field was not checked.
- Whether any journey fixture relies on a selection that does not exist on the fixture graph (which strict mode would turn into an error) was not checked; only the counts in section 2 were computed. The default keeps those journeys unaffected either way.
- The inferred-intent widening under evaluation-pending packs is reported from reading `retrieve`, not reproduced.
- Reproduction script: `/private/tmp/claude-501/-Users-arunmenon-projects-Engram/e7ae2272-e36c-47f1-b529-f419badd10ec/scratchpad/repro_seed_mode.py` (memory backend only, read-only against the saved draft).
