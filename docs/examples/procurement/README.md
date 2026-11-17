# HarborWorks procurement ontology pilot

Status: input preparation. Synthetic purchase-to-invoice scope; no live SAP connector.

## Planned sequence
1. Freeze the domain specification, normalized contracts, sample events and question oracle here.
2. Create a tenant-private workbench draft, upload the first three files, and ask the configured assistant to propose the domain pack. Core is mandatory; memory/user stay optional.
3. Review citations, model, unresolved decisions and limitations. Preserve the supplied questions and expected answers.
4. Validate and run the three stories through the real engine, then the Spanner-backed workbench UI. Inspect graph properties and rejection/lifecycle/retry behavior as well as answer scores.
5. Save the generated pack, evaluation artifact, run evidence and remaining limitations. Do not approve/activate a customer or connect to SAP.

## Inputs
- `01-domain-spec.md`: identity, relationships, lifecycle, trust, matching boundary and limitations.
- `02-event-contracts.json`: invented normalized event contracts, not SAP API schemas.
- `03-sample-events.json`: fixed sequence for clean purchase, partial-receipt mismatch and repeated IDs across companies; includes retry, ledger-only note, late state transition and malformed events.
- `04-questions.json`: seven expected answers fixed before model generation. Exact IDs belong to the saved evaluation artifact; operators select labelled entities in the UI.

## Public grounding, checked 2026-11-03
- https://www.concur.com/products/purchase-request — purchase requests and pre-spend approval.
- https://www.concur.com/products/three-way-match — purchase order, receipt and invoice matching.
- https://developer.concur.com/api-reference/invoice/v3.purchase-order.html — PO headers and line items, vendor codes, related request numbers, currency and receipt updates. Our field names, minor-unit money and event envelopes are normalization choices, not verbatim SAP contracts.

No company-specific Concur configuration was supplied. Scope, keys, trusted producer and single-line invoice constraints are explicit synthetic exercise decisions, awaiting real-customer validation. Actual API access, adapter development, financial policy and data migration are out of scope for this pilot.
