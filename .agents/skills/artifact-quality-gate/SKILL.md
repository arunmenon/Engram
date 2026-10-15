---
name: artifact-quality-gate
description: Review deliverables for concrete quality defects often called AI slop—unsupported claims, hidden assumptions, empty reasoning, filler, unnecessary complexity, misleading proof and unusable presentation. Use for a requested slop check, deliverable quality gate or substantive artifact audit across documents, code, plans and visual guides. Not an AI-authorship detector or a mandatory review of routine replies.
---

# Artifact Quality Gate

Review whether the artifact earns its claims, detail and complexity for its intended use. “Slop” here means avoidable content or implementation that looks useful or complete but does not deliver justified value. This is a working review definition, not a scientific classifier or judgment of the author.

A long explanation, technical vocabulary, an abstraction, an AI-generated origin or a particular writing style is not itself a defect. Name observable problems and consequences instead of calling the artifact “sloppy.”

## Establish the review contract

Identify the artifact/version, intended audience, task it must support, requirements and authoritative evidence. Infer these from the request and existing files; ask only when a missing decision changes the verdict. If no objective is available, report that limitation rather than inventing one.

State scope before the verdict. For a suite, inventory the included pages/files; inspect cross-artifact dependencies and material claims. If sampling, name the sample and do not extend its verdict to the whole suite. Reviewing a new diff may require unchanged context, but does not authorize an unrelated repository audit.

Read [artifact checks](references/artifact-checks.md) only for the relevant artifact modes. Read [research grounding](references/research-grounding.md) when explaining the term, methodology or limitations; ordinary runs can use the rubric below directly.

## Inspect seven dimensions

| Dimension | What must be earned | Observable defect |
|---|---|---|
| Grounding | Material claims match inspected sources and their scope. | Invented/irrelevant citation; wrong runtime branch; proposal described as implemented fact. |
| Reasoning and assumptions | Conclusions follow from evidence; important preconditions and causal steps are explicit. | Diagram implies ordering without a mechanism; one example becomes a universal guarantee. |
| Audience and task fit | The reader can understand and use the relevant substance. | Unintroduced concept; acronym expansion without meaning; generic advice that never answers the actual question. |
| Necessary detail and complexity | Each section, component and abstraction has a current purpose. | Repeated filler; wrapper/framework without an unmet requirement; simpler proposal loses no required behavior. |
| Verification honesty | Evidence supports the exact completion or quality claim. | Test count substitutes for coverage; acceptance/ACK substitutes for output; expected answers derived from actual output. |
| Consistency and presentation | Text, code, diagrams and examples communicate the same semantics. | Conflicting definitions; misleading arrows/axes; blank initial state; illustrative output presented as a real run. |
| Usability and handoff | The intended consumer can act without hidden repair or author-only knowledge. | A reproduction guide omits prerequisites; a decision has no criterion; a command is claimed runnable without supported inputs. |

Inspect claims where they matter; do not mechanically manufacture a finding for every row. Distinguish a correctness defect, missing explanation, unmet requirement, unnecessary work and an optional style preference.

## Require evidence for findings

For each substantive finding record: exact location, observed content/behavior, source or requirement establishing the discrepancy, consequence, smallest correction and a meaningful recheck. For a claim that cannot be verified, say what evidence is missing; lack of access does not prove it false.

Trace the actual configuration, construction and callers before judging a code-dependent claim. Check whether the source is current, legacy, proposed or merely a helper. Verify citations support the nearby claim, not just that a URL exists. Separate source inspection from execution and observed behavior from a broader guarantee.

Use counterexamples where decisive: absent optional pack; delayed worker; different owner; failed run followed by success; changed prerequisite. Keep examples faithful to inspected contracts and mark hypothetical outcomes. A comprehension question is a desk check, not a real learner study.

For possible bloat, identify the concrete cost and the requirement the simpler alternative still satisfies. Preserve essential validation, authorization, evidence, error handling, accessibility and material caveats. One caller or a large file is a signal to inspect, not proof to delete an abstraction. Do not shorten an explanation into another unexplained abstraction.

## Produce a scoped gate result

- **PASS:** no unresolved material defect or required evidence gap in the declared scope. Optional improvements may remain. This is not certification of the whole product or proof that no defects exist.
- **REVISE:** observed defects materially undermine correctness, understanding, intended use or a required claim. List what must change before this scope can pass.
- **BLOCKED:** required inputs/evidence are unavailable, preventing a defensible decision. Identify the precise missing item and report any confirmed defects separately. Do not infer failure from unfamiliar style or missing access.

Choose REVISE when a confirmed material defect already warrants it; retain unverified areas explicitly. Never give PASS while required verification remains unavailable. Do not average critical defects into a numeric “slop score” or infer AI authorship, deception or intent.

Lead with verdict, purpose and inspected scope. Then give prioritized findings, optional improvements and unverified scope as needed. A compact finding table works when there are multiple issues; a simple artifact may need only a paragraph. No quota of findings or paperwork. Preserve good mechanisms and useful depth, not just a list of cuts.

When revising the rubric, use [calibration cases](references/calibration-cases.md) to check false positives, evidence gaps and missed material defects; do not present a desk check as measured detection accuracy.

## Correct and recheck within authorization

Review is the default. Apply fixes only when requested or already authorized by the surrounding task. Recheck the affected claim, behavior or rendered interaction, including any invariant the edit could weaken. Use the established format-specific tools and project checks; do not claim UI verification from HTML inspection or functional correctness from compilation.

Report which findings are resolved and which remain. Keep failed evidence; never change an oracle, claim or scope silently just to pass. Stop when the requested gate is satisfied or a specific unresolved requirement blocks it; do not restart a broad audit for each minor edit.

This gate complements explanation, code review and test workflows. Reuse their evidence instead of duplicating reviews. It does not authorize agents, cloud runs, deployment, publication, issue closure or changes to approval gates. Automatic skill discovery may recognize “check for slop” or “run the artifact quality gate”; do not impose it on every routine response.
