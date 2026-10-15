# Checks by artifact type

Use relevant checks, not every mode. The purpose and intended consumer determine materiality.

## Explanations, architecture documents and guides

Can the reader explain why the component exists, what enters/leaves it and how the next component uses the result? Define consequential concepts before use, with a concrete effect. A distant glossary or a familiar name does not establish understanding. Check transitions from schema to instance, input to processing, condition to output and source to conclusion.

Inspect actual selected runtime branches for source-dependent explanations. A legacy function with a matching name can produce a confident but incorrect assessment of a newer path. Contradictory pages must be reconciled against sources, not made cosmetically consistent with one another.

Cut repetition that adds no new role, condition or consequence. Preserve technically necessary distinctions and optional depth. Expertise of the reviewer is not evidence that a newcomer understands the artifact; use comprehension questions and label the limits of desk review.

## Code and implementation designs

Compare the implementation with the real requirement and existing callers. Inspect invented APIs/dependencies, duplicated logic, hidden defaults, swallowed failures and ambiguous ownership/state boundaries. Ask what concrete present need an abstraction solves; compare a simpler alternative without removing required invariants.

A passing syntax check does not establish functionality; a happy path does not establish concurrency/retry safety. Reuse project tests/review evidence and identify what was not exercised. Keep legitimate interface boundaries, safeguards and useful comments even when removing them would reduce line count. This is not an exhaustive security or performance audit unless requested.

## Specifications, plans and verification reports

A task must have an observable result and meaningful acceptance criterion. Identify hidden prerequisites, unresolved decisions, dependency order and the difference between implemented, integrated and verified. “Support all packs” or “test everything” needs an explicit inventory and honest coverage boundary.

Expected results should be independently declared. A test should fail for a plausible broken implementation. Preserve rejection/no-effect cases and actual failed runs. Do not replace evidence with test counts, model/reviewer confidence, HTTP success or delivery progress.

## HTML, slides, diagrams and interfaces

Read diagrams against text and source. Explain arrows, state changes and boundaries. Do not imply serial worker execution, atomic transactions or causal relationships merely by connecting boxes. Distinguish allowed types from stored records and illustrative animation from live execution.

Inspect the rendered artifact when claiming usability: initial state, controls, navigation, legible labels, relevant narrow-screen behavior and a usable text equivalent. Source-only review can flag problems but cannot establish rendered success. Avoid decorative graphs and enormous tables that hide the decision or mechanism.

## Research briefs, comparisons and data artifacts

Match each consequential claim to an inspected source, its actual version and study limits. Separate empirical results, self-report, commentary and your synthesis. Verify fabricated metrics, citations, denominators, units, comparison baselines and unsupported extrapolation. An unrelated authoritative citation does not validate a claim.

For charts/tables inspect labels, axes, missing values and transformations. Do not treat precision or attractive formatting as proof. Say what a conclusion would change for the reader; irrelevant facts can be accurate yet still clutter the decision.
