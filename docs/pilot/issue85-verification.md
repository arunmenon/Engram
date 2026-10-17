# Issue85: historical design retrieval verification

The external reproduction exposed a real gap in the pilot's retrieval coverage. The original word-seeded test expected old versions to be filtered, but did not check an explicitly requested old version or the approval branch after filtering. Traversal found v1 and its approval; admission removed v1 and the edge, leaving misleadingly detached approval context. The old approval was not actually rewired to v2.

## Correction and decision

A caller-given superseded artifact remains present with `retrieval_reason: superseded`. Other discovered historical nodes keep the pack's existing status/why policy: trace is a filtered current view unless the historical identity is explicitly requested. [ADR0018](../adr/0018-ontology-packs.md) records this deliberate choice.

The API exposes `meta.excluded_nodes` with admission reasons and `meta.excluded_edges` with original relationship endpoints. Traversal-only branches disconnected from surviving seeds are removed before source provenance is attached. An independently requested approval remains a requested result, with its omitted APPROVES→v1 relationship explicit; no v2 approval is invented. Capacity truncation and missing IDs remain distinct from admission exclusion. Existing trust policy stays in force.

## Expected versus actual

Run `issue85-1017-03`, executed source `9ab90e4`, passed all 95 checks: four newly accepted inputs, 16 authenticated public HTTP requests, 22 actual gpt-6-luna calls returned, five final worker lags zero, clean shutdown and final retained-data/owner/queue conservation. Inputs went through the public dispatcher, ledger, normal workers and real retained Spanner target. A remained inactive and unchanged; B produced the requirement, v1 design, Priya's approval and v2 revision. No direct graph insert, reset or repair was used.

| Frozen question | Expected and observed |
|---|---|
| Trace seeded on v1 | v1 remains and is labelled superseded; no exclusion entry for it |
| Trace seeded on v2 | v1 excluded with reason; its traversal-only approval excluded as filtered_path |
| Trace seeded on requirement | Same exclusion/approval integrity; v2 and requirement remain |
| Word-seeded trace | Existing filtering retained; no detached approval branch |
| Status seeded on v1 | Existing historical behavior retained, exact APPROVES→v1 edge |
| Why seeded on v1 | v1 retained and labelled; no new APPROVES traversal weight added |
| Keyword-free query seeded on v1 | Explicit v1 remains and is labelled |
| Explicit approval plus v2 seeds | Approval stays independently selected; metadata names its omitted v1 target; no APPROVES→v2 edge |

The independent [saved-run auditor](../review/spanner-compatibility/runs/issue85-1017-03/audit_saved_run.py) checks each exact public response, exclusion/edge identity, no dangling returned edge and no v2 approval. It also verifies all 183 execution source hashes against the recorded commit. Run it from the repository root with Python 3. [Results](../review/spanner-compatibility/runs/issue85-1017-03/results.json), [eight-query audit](../review/spanner-compatibility/runs/issue85-1017-03/approval-exclusion-audit.json) and [source audit](../review/spanner-compatibility/runs/issue85-1017-03/recorded-source-audit.json) are retained.

Local proof: the issue's original projected in-memory script is archived with before/after output; 38 PDLC tests and 165 affected route/model/retrieval tests passed (overlapping sets). Both changed runtime files passed mypy and Ruff. Status/why controls follow their existing edge weights. These checks do not establish a stronger general history, trust, ranking or deployment guarantee.

## Retained failures and review

Attempt01 stopped before any HTTP requests/model calls because its fixture omitted the exact committed P04 negative-delivery declaration. Attempt02 accepted one requirement, then failed because the authored expected graph omitted the pack-declared Requirement→Spec REFINES link. Both remain failed and their data/evidence are preserved. Attempt03 loads that original negative proof and validates all four authored edge sets against the declared pack rules before execution; the eight retrieval questions/expectations are unchanged. No answer was reworded to manufacture a pass.

Astra accepted the bounded source design and final live evidence, including the independently requested approval case, source audit, shutdown and conservation. Issue85 was closed after the evidence disposition; the broader umbrellas and other open gaps remain separate. The study-book corrections are documented in [retrieval errata](../guide/retrieval-errata.md), and page 17 of the main HTML guide explains the new diagnostics with a saved rendered check.

To repeat the write journey, follow the existing [team prerequisites](team-walkthrough.md), use a fresh run/identity namespace, freeze [the same cases](issue85-1017-03-journeys.json), obtain a fresh read-only model-transition inspection, then invoke `engram_pilot_first_run.py --journeys-only --journey-file <frozen-file> --predecessor <inspection> --run-id <new-id> --output <new-directory>`. Do not replay these retained Event IDs and call that fresh creation.
