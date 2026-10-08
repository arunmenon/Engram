# Foundation design necessity review

Perform one bounded Astra review of the foundation design. Deliver a design decision table for stakeholder review. Do not implement recommendations or run tests/cloud experiments.

## Review inputs

Checkout: /Users/arunmenon/projects/Engram-foundation-gate. Inspect the foundation source additions between walkthrough commit 27b4ba861814163d4292a950ddaae484a4282d82 and snapshot commit f6fd87ce1086522bdc6fea1846d92ab9d6f50f31. Use the dependency inventory and previous source review to locate relevant code, then inspect actual source and representative tests as design evidence. Read selectively; raw execution logs are unnecessary. Branch coordinates are review inputs, not material to repeat in the design artifact.

## Design questions

For each coherent addition group:
1. What concrete problem does it solve? Explain with a plain-language example and precise code references.
2. Which agreed platform requirement needs it: tenant isolation/database binding; mandatory core and composable optional packs; event contracts/admission; immutable acceptance/source identity; correct processing/evidence/retrieval? Is it necessary to that design, an extension to defer, or unsupported complexity?
3. Are state, validation, ownership logic or abstractions duplicated? Distinguish necessary checks at separate trust/transaction boundaries from redundant checks.
4. Is there a simpler implementation using existing primitives that retains the requirement? Name the concrete alternative and its design tradeoff; do not introduce another framework or service.
5. Are module boundaries, dependency direction and shared helpers clear? Separate runtime complexity from test harnesses, lock files and retained historical evidence. Large evidence files alone do not constitute runtime bloat.

Cover tenant/database binding and fencing; event contracts/admission/source trust; acceptance receipts/duplicate identity; worker handoffs/disposition and retrieval gating; pack projection/composition primitives; supporting settings/storage/schema/helpers/tests. Account for source-delta groups in the decision table or a brief design-coverage appendix. Peripheral and migration-related additions may be classified for deferral without migration analysis. Do not remove safeguards because a demo uses one tenant.

## Output: design only

Save docs/review/spanner-compatibility/2026-10-08-foundation-necessity-astra-review.md with:
- Short design assessment.
- Decision table: component/files; purpose/example; governing design requirement; keep/simplify/defer recommendation; concrete alternative/action; design tradeoffs.
- Prioritized design findings with source references and supported simpler alternatives. State uncertainty rather than inventing bloat.
- Brief component coverage appendix if needed.

Do not include a status section, G01–G03 progress, execution history, cloud verification/test-pass claims, 'verified on real Spanner/foundation branch' framing, readiness statements, operational known-gap summaries or publication progress. The stakeholder explicitly wants the artifact to explain and assess the design, without those distractions. Preserve existing evidence elsewhere; do not edit or delete it.

Read-only source review. Only write the requested review report. No code/test edits, execution, issue updates, migration work, additional agents, G04 or automatic implementation/review loop. Recommendations are for stakeholder decision, not authorization to change code.
