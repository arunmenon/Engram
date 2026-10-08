# G05 verification and stakeholder walkthrough

Status:39real-Spanner checks passed and scoped Astra evidence review found no blockers. Dataset retained by explicit stakeholder instruction; G05 cloud run is complete. Stakeholder sign-off is not inferred.

## What happened

Engram rebuilt one connected password-reset story: approved planning artifacts, implementation ticket, PR, changes-requested and approved reviews, failed and passing test runs, release, failed/successful production deployments and staging. Newsletter artifacts deliberately reused local identifiers but stayed out of password-reset answers. An unlinked deployment stayed unlinked.

Source commit684b0cc; run20261008-cloud-g05-all-01;193source hashes checked against the pre-execution archive. Private bound compat-control tenant; core1.1+PDLC3.0; memory/user disabled; real HTTP authentication,Spanner ledger,all five ordinary workers,Spanner graph and HTTP retrieval. Inputs are explicitly synthetic normalized producer events; native adapter compatibility is not implied.

## Fix and preserved failures

#50 records loose-word seed widening: descriptive words such as production independently seeded unrelated journeys even when an exact artifact was supplied. The minimal correction disables loose-word fallback once explicit seeds resolve, retaining independent key/number/pattern references and text-only discovery. Original questions and exact expected sets stayed unchanged. Local failure was reproduced before the fix;52focused tests passed afterwards. Broader suite:66passed,1failed. The owner-query failure also occurs on unchanged HEAD and is retained in the local run folder; it is not reported passing or fixed here.

Real pack extraction applied outcomes were logged for both design events. Three incompatible proposed links were rejected (Decision→Spec and Constraint→DesignElement/Requirement via APPLIES_TO). Valid proposals were separately recorded. These rejections do not imply whole extraction behavior is proven; deterministic declared journey links remained exact.

## Inputs and processing

31HTTP inputs:27unique accepted events,1unchanged duplicate,1unchanged conflicting-ID409,and2unchanged invalid422requests. All four no-write responses have complete seven-table fingerprint checks. Every accepted step checks ledger payload and trusted binding metadata,worker progress,declared graph/evidence and retrieval. LLM-generated nodes remain separately attributable; expected answers do not derive from runtime responses.

| Input | HTTP | Recorded result |
|---|---|---|
| IM01 | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM02 | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM03 | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM04 | 201 | passed; ledger/graph/read or no-write evidence in observations |
| CJ-approval | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM05 | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM06 | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM07-requested | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM07-approved | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM08-failure | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM08-success | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM09-spec | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM09-requirement | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM09-ticket | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM09-change | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM09-test | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM10-change | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM10-test | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM11-duplicate | 201 | passed; ledger/graph/read or no-write evidence in observations |
| IM11-conflict | 409 | passed; ledger/graph/read or no-write evidence in observations |
| IM12-revision | 422 | passed; ledger/graph/read or no-write evidence in observations |
| RD02-merge | 201 | passed; ledger/graph/read or no-write evidence in observations |
| RD03-release | 201 | passed; ledger/graph/read or no-write evidence in observations |
| RD04-failed | 201 | passed; ledger/graph/read or no-write evidence in observations |
| RD05-succeeded | 201 | passed; ledger/graph/read or no-write evidence in observations |
| RD06-staging | 201 | passed; ledger/graph/read or no-write evidence in observations |
| RD09-empty-release | 201 | passed; ledger/graph/read or no-write evidence in observations |
| RD09-unlinked-deploy | 201 | passed; ledger/graph/read or no-write evidence in observations |
| RD10-other-release | 201 | passed; ledger/graph/read or no-write evidence in observations |
| RD10-other-repo-same-time | 201 | passed; ledger/graph/read or no-write evidence in observations |
| RD11-null-release | 422 | passed; ledger/graph/read or no-write evidence in observations |

## Eight retrieval journeys

Every query checks exact nodes,declared edge topology/properties,newest event provenance,no forbidden IDs and no truncation. The full input and API answer appear in observations.json; frozen expectations in fixtures.json.

| Query | Meaning | Expected artifacts | Result |
|---|---|---|---|
| CQ1-requirement-to-production | Requirement through planning/code/tests/release/deployment | 17 | PASS |
| CQ2-release-to-requirements | Release back to planning and requirements | 17 | PASS |
| CQ3-deployment-to-verification | Successful deployment to its code and verification | 15 | PASS |
| CQ4-production-outcomes | Compare failed/successful production attempts, excluding staging sibling | 16 | PASS |
| CQ5-design-to-shipping | LLD to implementation and shipping | 17 | PASS |
| CQ6-text-discovery | Text-only fifteen minutes discovery | 17 | PASS |
| CQ7-unrelated-feature | Newsletter journey without password-reset artifacts | 9 | PASS |
| CQ8-unlinked-deployment | Unlinked deployment and component only | 2 | PASS |

## Retained state and repeat boundaries

Target:projects/portiq-mvp/instances/engram-experiment/databases/engram-compat-target. Active epoch43,PDLC3.0. Retained:27ledger events,63graph nodes,102edges,5consumer groups,80cursors,zero deliveries and dead letters. Workers and HTTP server stopped cleanly. Exact keys/fingerprints are in retained-dataset.json. No cleanup ran. User subsequently explicitly requested retention.

Do not rerun the empty-activation driver against this nonempty target,advance its bundle,delete,or reuse it. A fresh run needs an independently authorized empty database or explicit approval to clean/reuse this one. G06 uses a separate database. Credentials remain private and are not committed.

## Recorded stakeholder demo

1. Start with the expiry requirement. Show its PRD,HLD/LLD and version-bound approval; follow the ticket and PR.
2. Show Alex requesting changes and Robin approving as separate Review artifacts. Show both failed and passing TestRuns; coverage is not a passing result.
3. Follow release and deployments. Failed production,successful production and staging remain distinct. Compare the production attempts with explicit seeds.
4. Start from release or LLD and retrieve the expected chain with source events. Start from the successful attempt and explain why sibling deployment attempts stay out.
5. Ask the unchanged natural-language production question and the text-only fifteen minutes question. Show exact password-reset artifacts and absence of newsletter/unlinked records; this exercises #50 on Spanner.
6. Retrieve newsletter and the unlinked deployment separately. Show no fabricated implementation/release links.
7. Show duplicate/conflict/invalid no-write evidence and the retained state. Explain that this is one bound tenant and a bounded journey,not whole-pack/platform compatibility.

## Limits and issue assessment

Synthetic normalized producers,private bound tenant,serve_unevaluated,no full multi-tenant dispatcher,whole-pack or baseline65 sign-off. Monitoring export403 remains unresolved and is not a data-path success claim. No migration,Redis/Neo4j runners or foundation-track reruns.

#50 is the scoped reproduced and corrected defect; close only after published evidence. #34/#35/#36/#37/#39/#40/#41 get bounded evidence updates and remain open. No additional feature bucket needed for G05; it belongs to connected PDLC journeys. Separate ANN#48 and hierarchy#49 are not executed. G06 tickets are separately approved.

Evidence: [fixtures](runs/20261008-cloud-g05-all-01/fixtures.json),[observations](runs/20261008-cloud-g05-all-01/observations.json),[retention](runs/20261008-cloud-g05-all-01/retained-dataset.json),[source archive](runs/20261008-cloud-g05-all-01/executed-source.tar.gz),[hashes](runs/20261008-cloud-g05-all-01/executed-source-sha256.json),[runner log](runs/20261008-cloud-g05-all-01/runner.log),[Astra source review](2026-10-08-astra-g05-source-review.md),[Astra evidence review](2026-10-08-astra-g05-evidence-review.md). Actual issue reconciliation receipts follow as a separate JSON record.
