---
schema_version: 1
artifact_id: N-20260929-13
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104604060825367006", "file_id": null, "sha256": null}, {"artifact_id": "post:2104615324855517343", "file_id": null, "sha256": null}, {"artifact_id": "WR-20260928-05", "file_id": "1ji5imL2NsBiFi4diw96efDjyoZZH5qNH", "sha256": "ce64cea9d09578cc7dddde62bc3504a0475fba3ff3d31633fd5ac0f96c7d53c1"}]
supersedes: null
idempotency_key: note:docs:palantir.com/docs/foundry/action-types/submission-criteria
claim_cluster: docs:palantir.com/docs/foundry/action-types/submission-criteria
feeds: ["memory"]
primary_source: https://www.palantir.com/docs/foundry/action-types/submission-criteria/
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R10
pillar_secondary: ["R8"]
memory_stage: safety
priority: 3
tags: {"mechanism": ["typed-action-contract", "pre-submission-conditions", "per-condition-failure-message", "nested-all-any-none"], "workload": ["ontology-backed-agent-actions"], "lifecycle_stage": ["act"], "cross_cutting": ["shared_state"]}
evidence_grade: {"directness": "high: the vendor's own documentation page states the condition types, operators, combinators and failure-message behaviour", "control": "unknown: documentation, no measurement of effect", "independence": "low: single vendor source; the posts only paraphrase Palantir's docs", "reproducibility": "medium: public page, but unversioned; retrieved text is paraphrased by the fetch tool except for quoted sentences", "applicability": "medium: a concrete pattern for a check before an agent acts on PDLC objects; no evidence it improves agent outcomes"}
beliefs_affected: {"supports": ["B25"], "contradicts": [], "would_create": []}
claim_correction: The post says agents act only through a fixed list of typed actions; the documentation shows submission criteria gate who and with what parameters an action may be submitted, and explicitly do not replace base permissions.
---

# Palantir Foundry action types: submission criteria (conditions checked before an action is submitted)

- **URL:** https://www.palantir.com/docs/foundry/action-types/submission-criteria/
- **Type:** vendor documentation
- **Author / org:** Palantir Technologies (Foundry documentation)
- **Date:** not stated on the page (unversioned docs)
- **Retrieved:** 2026-09-29 (live page; no version or revision id shown). Text below is quoted where it is in quotation marks and otherwise paraphrased from the fetched page.
- **Cited by evidence:** @ZaneOnAI https://x.com/ZaneOnAI/status/2104604060825367006 ("The agent never sees tables. It sees business objects ... and a fixed list of actions it can take on them"); @automater_ai https://x.com/automater_ai/status/2104615324855517343 ("Ontology isn't a schema nicety; it's the blast-radius boundary"). Requested by watch request WR-20260928-05 (challenger, for experiment E-20260928-13).
- **Relevance to a memory stack:** medium. It is the concrete product mechanism behind the "Action-type contract" proposed for our PDLC ontology: typed actions whose submission is blocked unless declared conditions pass, each with its own failure message.

## TL;DR
- "Submission criteria (formerly known as validations) are the conditions that determine whether an action can be submitted." An action is submittable only when all criteria pass.
- Three condition templates: Current User (user id, direct or inherited group membership, multipass attributes such as Organization), Parameter (values passed to the action), Execution Context (whether the action runs inside an Ontology Scenario). Attachment and object-set parameters are unsupported.
- Conditions combine with nestable logical operators requiring all, any or none of the child conditions to pass.
- "Every condition and logical operator on the root level has its own failure message", shown to the user to explain why submission is blocked.
- **Claim correction:** submission criteria encode business rules on top of permissions; they do not replace base permissions (page overview). The post's "your agent gets exactly the permissions of the user who runs it" is a separate claim about access checks, not documented on this page.

## What it claims / describes
An action type in Foundry is a typed edit on ontology objects with declared parameters. Submission criteria are evaluated when a user (or an application acting for a user) submits the action. They are independent of who may edit the action type itself. Per the page, they exist to "encode business logic into data editing permissions" for data quality and governance.

**Condition templates.**
1. Current User: compares the submitter's user id (as a string, against a static list or a string parameter), group memberships (direct or inherited), or multipass attributes (for example Organization).
2. Parameter: compares values of the action's own parameters.
3. Execution Context: distinguishes submissions inside an Ontology Scenario (a what-if sandbox) from normal submissions, so different rules can apply.

**Operators.** Single-value: is, is not, matches, is less than, is greater than or equals. Multi-value: includes, includes any, is included in, each is, each is not.

**Combination.** Logical operators nest; each requires all, any or no underlying conditions to pass.

**Failure messages.** Each root-level condition and logical operator carries its own failure message, displayed when that criterion fails.

Related pages linked (not fetched): Test run (`/docs/foundry/action-types/test-run/`), Ontology Scenarios (`/docs/foundry/ontology/overview-ontology-scenario/`).

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| condition templates | 3 (Current User, Parameter, Execution Context) | | documentation | no measurement |
| logical combinators | all, any, none (nestable) | | documentation | |
| failure messages | one per root-level condition or operator | | documentation | |

No quantitative results exist on this page.

## Mechanism details you could implement
For a PDLC check before an agent acts (priority 3), a minimal equivalent (inference, modelled on the page):
```text
action_type: link_pr_to_requirement(pr_id, requirement_id, link_type)
submission_criteria:
  all:
    - current_user.groups includes "repo-maintainers"        -> "Only maintainers may assert trace links"
    - param.link_type is included in ["implements","verifies","refines","satisfies","blocks"] -> "Unknown trace link type"
    - param.requirement_id each is not <status=retired>      -> "Cannot link to a retired requirement"
    - execution_context is not scenario OR dry_run is true   -> "Scenario edits cannot write to the live graph"
```
- Evaluate criteria in code before the write, not by the model; return the failing criterion's message to the agent so it can repair the call.
- Keep criteria declarative and versioned next to the ontology schema so a change to the schema forces a review of its criteria.
- Use the scenario/dry-run distinction to let agents propose links in a sandbox that a person or a decision model then promotes.

## Limitations, caveats, counter-evidence
- Documentation of a feature, not evidence that it reduces agent errors or improves outcomes; this establishes the product attribution only (the watch request itself says so).
- The page is unversioned; the retrieved text may change. The fetch tool paraphrased parts of the page; only quoted sentences are verbatim.
- Conditions cover user identity, parameters and execution context only; object-property conditions on the target objects are not listed among the three templates as retrieved (attachment and object-set parameters are explicitly unsupported), so "cannot link to a retired requirement" may need a parameter-derived value or a separate function (inference).
- Nothing on the page addresses agents specifically; applying it to agents is the posts' framing.

## Takeaways for tuning a memory stack
- A write into the context graph proposed by an agent (for example a trace link) should pass declared, typed pre-conditions with per-condition error messages before it lands; this is a concrete, vendor-proven interface shape for that check.
- Permissions and business-rule criteria are separate layers; keep both.
- Distinguish sandbox (scenario) writes from live writes in the criteria.

## Open questions
- Does the Test run page document dry-run semantics that fit a propose-then-promote flow for agent-written links?
- Can criteria reference properties of the target objects (not only parameters), for example a requirement's status?

## Grading and labels
- Directness: high; the vendor's own page.
- Control: unknown; no measurement.
- Independence: low; one vendor source.
- Reproducibility: medium; public but unversioned.
- Applicability: medium; directly usable interface pattern for the PDLC check-before-act, no outcome evidence.
- Strength: vendor-benchmark (closest label on the scale for vendor documentation; there is no benchmark).
- Pillars: R10 primary (ontology and typed actions on the context graph); R8 secondary (execution authority). Memory stage: safety. Priority 3.
- B25 supports: the action is authorised by declared criteria evaluated outside the evidence and the model, not by the content proposing it.
- Contradiction rows: none.

## Origin chain
- Posts @ZaneOnAI 2104604060825367006 and @automater_ai 2104615324855517343 (2026-09-28) -> Palantir Foundry docs, Action types, Submission criteria page (retrieved 2026-09-29) -> this note. Also answers WR-20260928-05.
- Independence: related bus note `docs:palantir.com/docs/foundry/ontology` covers the Ontology overview from the same vendor; this note adds the action-level gate.
