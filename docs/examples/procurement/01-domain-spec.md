# HarborWorks procurement pilot — synthetic domain specification

## Scope and evidence
This is an invented customer and invented operational data. It is a purchase-to-invoice pilot,
not employee expense reporting, a live SAP Concur connector, or a payment system.
Concur's public Purchase Request, Purchase Orders v3 and Three-Way Match documentation ground
the business vocabulary. The procurement.* events below are OUR normalized synthetic interface,
not SAP webhook names, SAP statuses or an implemented SAP adapter.

## Composition
The domain pack is procurement_ops, version 1.0.0, requiring core>=1.1 only.
Core supplies Sourced, Lifecycled and event provenance. User and memory are optional add-ons;
do not duplicate their concepts or make them mandatory. Requester and approver IDs are opaque
source identifiers in this slice, not User nodes or grants of authorization.

## Identity and vocabulary
Company is part of every key. Document numbers repeat between us and eu within ONE tenant.
The seven domain types and ordered keys are:
- Supplier: [company_id, supplier_id]; supplier name is descriptive, never identity.
- PurchaseRequest: [company_id, request_id]; description, requester_id, amount_minor, currency;
  approval evidence adds approver_id and decision_id; rejection adds rejected_by and reason.
- PurchaseOrder: [company_id, order_id]; request_id, supplier_id, currency.
- PurchaseOrderLine: [company_id, order_id, line_id]; description, quantity, unit_price_minor.
- GoodsReceipt: [company_id, receipt_id, line_id]; order_id, received_quantity.
- ProcurementInvoice: [company_id, invoice_id]; order_id, line_id, supplier_id, quantity,
  amount_minor, currency. This FIRST slice allows exactly one referenced order line per invoice.
- MatchAssessment: [company_id, assessment_id]; invoice_id, verdict, ordered_quantity,
  received_quantity, invoiced_quantity and reason. Each assessment has a separate source ID.

Relations (all scoped by company): PurchaseOrder FULFILLS_REQUEST PurchaseRequest;
PurchaseOrder ORDERED_FROM Supplier; PurchaseOrder HAS_ORDER_LINE PurchaseOrderLine;
GoodsReceipt RECEIVES_LINE PurchaseOrderLine; ProcurementInvoice INVOICES_ORDER PurchaseOrder;
ProcurementInvoice BILLS_LINE PurchaseOrderLine; MatchAssessment ASSESSES_INVOICE ProcurementInvoice.
Receipt quantities are per receipt, not cumulative. Different receipts must not overwrite one another.
Supplier, request and order records arrive before their dependents in this pilot.

## Lifecycle and update decisions
A PurchaseRequest starts submitted; approved and rejected are terminal states.
request.approved moves only submitted -> approved; request.rejected only submitted -> rejected.
Approval/rejection events also upsert the request for provenance. Missing descriptions on those
events preserve the description. These are guarded graph updates, not enforcement of spend authority.
The deliberate rejection after approval must leave the request approved; the event can still be
admitted and its other graph writes recorded. A failed state guard is not an ingest rejection.
Other types have no lifecycle in this slice. An invoice is NOT marked paid by a match assessment.
A repeated normalized event with the same event_id and same payload is an idempotent retry.
No source may reuse a semantic record ID for conflicting facts; conflict policy is a future adapter concern.

## Amounts, quantities and source authority
All money is integer minor units plus currency; this fixture uses USD or EUR (two decimal places).
Whole-item quantities only. No tax, discount, exchange-rate conversion, fractional units or tolerances.
The trusted synthetic producer is procurement-adapter. Trust is configured outside the payload.
Every type uses Sourced. Ordinary domain retrieval excludes untrusted uncorroborated discoveries.

## Matching boundary
The assessment verdict is an observation FROM a source matching process, never calculated by the pack.
Allowed verdicts are matched, quantity_mismatch, missing_receipt. The quantities and reason are evidence.
In the mismatch story, ordered=10, received=4+6=10, invoiced=12. The source reports quantity_mismatch.
Engram stores this evidence and answers graph questions. It does not implement three-way arithmetic,
matching rules, tolerance approval or a live Concur reconciliation service.

## Journeys and fixed expectations
J1 Clean purchase: US PR-100 submitted then approved, PO-100 with one line for 10 monitors at
10000 USD minor units each, receipt GR-100 for 10, invoice INV-100 for 10 and 100000 minor units,
assessment M-100 matched. A late rejection event must not change approved back to rejected.
J2 Partial delivery and mismatch: US PR-200 approved, PO-200 line 1 orders 10 keyboards at
10000 minor units, receipts GR-200A=4 and GR-200B=6, invoice INV-200 bills 12 and 120000 minor units,
assessment M-200 quantity_mismatch. Both receipts remain distinct.
J3 Identifier collision: EU reuses supplier VEN-1, request PR-100, order PO-100, line 1,
receipt GR-100, invoice INV-100 and assessment M-100. These are different EU records, in EUR.
US and EU orders must have only their own invoices, receipts and assessment links.

Questions are frozen in 04-questions.json before generation. They select explicit starting entities,
use inbound one-hop retrieval for the named relationship and return the indicated answer type.
Do not change expected answers to make a run pass. Additional source specifications must resolve
unsupported requests rather than inventing engine options.

## Known limits and open production decisions
No multi-line invoices, service/amount-based receipts, allocations, supplier address variants, credit notes,
returns, cancellation, amendments, multi-stage approvals, payment execution, tax or general ledger.
No late-arrival repair, upstream polling, webhooks, SAP credentials or integration testing.
No enforced graph cardinality or traversal-wide company isolation. This is one tenant with companies.
Actual Concur product licensing, customer schemas, company boundaries, approval policies and real
source IDs must be supplied before treating this as a customer-specific integration.
