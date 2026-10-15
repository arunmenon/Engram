# Explain with Depth — bounded Astra review

Date: 2026-10-15  
Scope: `explain-with-depth/SKILL.md` and `agents/openai.yaml`. One read-only desk review of the skill; this report is the only written artifact. No operational, browser, database or API tests, delegation, or empirical learner testing.

## Verdict

**Ready to use; no blocking findings.** The skill supplies a coherent method for reducing clutter without removing causal explanation. It makes audience and intended learning outcome explicit, introduces concepts before implementation names, traces state across boundaries, and preserves material qualifications in the main explanation. Optional depth supports engineers without requiring newcomers to read exhaustive contracts. The prohibition on treating acknowledgement as proof of successful behavior is particularly useful for the supplied subject.

HTML support is appropriately scoped: initial state, meaningful controls, accessible alternatives, responsive layout and rendered checks are covered, while format-specific implementation is delegated to existing tools. A new HTML framework or detailed browser checklist would add maintenance cost without improving this skill's core purpose.

## Findings

| Severity | Location | Finding and likely effect | Minimal change |
| --- | --- | --- | --- |
| Low | `agents/openai.yaml`, `interface.default_prompt` | The default prompt offers only “plan or review,” although the description and skill explicitly support writing/drafting. Users launching it for a new explanation may be steered into a plan when they intended an artifact. | Change “plan or review” to “plan, write or review.” |

No material gap in the core workflow warrants an additional section. Audience, causal mechanism, sources, uncertainty, examples, comprehension checks and rendering are already addressed. Avoid expanding these into mandatory templates for every artifact.

## Justified extension only

One optional sentence would make the existing comprehension-check instruction more diagnostic: “Include a question about a changed condition or a plausible misconception, rather than only asking readers to repeat the described steps.” Put it beside the existing comprehension-question guidance. This earns its small cost by testing whether the explanation supports transfer; it does not require more questions or claim learner validation. The skill is usable without this addition.

## Desk-check application

The following order applies the skill to the supplied raw subject. The raw subject is the sole factual basis for this exercise; repository behavior has not been independently verified.

Assume a developer who understands basic event processing but does not know this system. Intended outcome: explain who requests work, who accesses storage, how selected capabilities affect processing, and what an ACK does and does not establish.

1. **Purpose and two separate things to track.** Introduce an event in the ledger and a delivery being handled by a worker. Establish that completing a delivery and retaining its underlying event are compatible. Do not infer broader replay or durability guarantees.
2. **Actors and boundaries.** The worker asks the `Subscription` interface for a batch. `SpannerSubscription` implements the storage-facing behavior, reading group cursors and pending deliveries through the Google Spanner Python SDK. Introduce “SDK” as the database client library. The worker determines processing; the subscription adapter performs database access. Explain the precise cursor contract only after consulting its source.
3. **One item through processing.** Follow one delivered event from the returned batch through the worker and graph adapter. Name the selected pack capabilities and explain how they determine applicability before presenting any graph output. A sequence diagram can distinguish the worker, subscription interface/implementation, database SDK, database and graph adapter without making them all equal abstraction layers.
4. **Completion and before/after state.** Show the pending delivery before processing and its cleared state after ACK; the ledger event remains. Keep the ACK meaning visible in the main explanation.
5. **A consequential variant.** Apply the same path to an event for which the selected capabilities yield no applicable output. Explain that ACK can still occur. Explicitly prevent the mistaken inference “ACK means the graph changed.” Do not invent which checks or policy authorize ACK.
6. **Optional engineering depth.** Provide source-backed cursor queries, payload contracts, pack selection rules and error/retry behavior only when verified and relevant. The supplied subject does not establish transaction boundaries, failure guarantees, delivery cardinality or exact graph mutations; mark those as questions to resolve, not implied properties.

### Three comprehension checks

1. **Who accesses Spanner when a worker asks for a batch?** Expected answer: the worker calls the `Subscription` interface; `SpannerSubscription` reads the group cursors and pending deliveries through the Google Spanner Python SDK. The interface is the boundary, and the implementation handles database access.
2. **After a delivery is acknowledged, what is cleared and what remains?** Expected answer: ACK clears the delivery; it does not clear the ledger event. The statement alone establishes no further replay or retention guarantee.
3. **The worker ACKs an event but produces no applicable output. Does that contradict the described design?** Expected answer: no. Shared workers apply selected pack capabilities, and ACK can mean there was no applicable output. ACK alone therefore does not demonstrate a graph change. Exact applicability and acknowledgement policies require their contracts.

This desk check demonstrates that the instructions can organize the supplied material without dropping its important distinction between processing completion and output. It is not evidence of learner comprehension or validation of the underlying implementation.

## Coordinator disposition

Both recommendations applied: the invocation prompt now includes writing, and comprehension checks include changed conditions or misconceptions. Structural validation passed after the edits. This was one Astra low-effort review; no second review or empirical learner testing is claimed.

Installed entrypoint: `/Users/arunmenon/.codex/skills/explain-with-depth/SKILL.md`. Invocation: `$explain-with-depth`. Automatic discovery remains enabled by default. The skill supports the approved content workflow; the pilot HTML has not been edited by this task.
