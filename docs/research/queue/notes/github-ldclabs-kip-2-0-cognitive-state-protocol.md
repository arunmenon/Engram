---
schema_version: 1
artifact_id: N-20260930-13
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105176462269780012", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:ldclabs/kip
claim_cluster: github:ldclabs/kip
feeds: ["memory"]
primary_source: https://github.com/ldclabs/KIP
source_commit: 69a05ff71e5c1ef759311432151b1a28d6aa749a
strength: repo-pinned
pillar_primary: R2
pillar_secondary: ["R10", "R1", "R8"]
memory_stage: linking
priority: 3
tags: {"mechanism": ["typed change histories", "supersession vs temporal succession vs recording repair", "belief computed at read time", "dependency validity", "deterministic conflict policy", "processing receipts"], "workload": ["personal agent memory", "knowledge graph of claims"], "lifecycle_stage": ["linking", "staleness", "consolidation"], "cross_cutting": ["shared_state"]}
evidence_grade: {"directness": "medium", "control": "low", "independence": "low", "reproducibility": "high", "applicability": "medium"}
beliefs_affected: {"supports": ["B25"], "contradicts": [], "would_create": ["A single supersedes edge conflates three different histories (the actor was wrong, the world changed, the memory recorded it wrong) and loses the answer to what was true then", "A derivation built on a revised root should become needs_review at read time, never be auto-retracted"]}
claim_correction: none
---

# KIP 2.0 (ldclabs/KIP), the memory protocol behind Anda Bot 0.13.0: three typed change histories, belief computed at read time

- **URL:** https://github.com/ldclabs/KIP
- **Type:** repo (protocol specification, normative draft)
- **Author / org:** LDC Labs (Anda Bot, anda-db, anda-brain). MIT License.
- **Date:** commit read `69a05ff71e5c1ef759311432151b1a28d6aa749a` (2026-09-27 17:13:48 +0800, "docs(kip): standardize Chinese epistemic terminology"). Anda Bot 0.13.0 announced 2026-09-30.
- **Retrieved:** 2026-09-30, shallow clone at repos/KIP. Read: README.md, SPECIFICATION.md sections 13.8, 14 (Assertion Lifecycle), 18.4, 21 (Epistemic Model), 25.4 (Temporal succession), 57 (KML Revision Rules); KIP-2.0-Memory-Interface.md sections 4 to 6. Not read: grammar, schemas, conformance fixtures, the brain/ policy documents. Nothing in the clone was executed.
- **Cited by evidence:** https://x.com/AndaBotHQ/status/2105176462269780012 (@AndaBotHQ, Anda Bot 0.13.0 release post). Memory digest of 2026-09-30 ("Corrections get a type").
- **Relevance to a memory stack:** high for supersession design. It is the most explicit written contract found so far for how a memory should record a correction, a change in the world, and its own extraction error as three different things, with a deterministic rule for conflicts. It is a specification with conformance cases, not a measured result.

## TL;DR
- A stored Proposition is truth-neutral. An Assertion is one actor's stance toward it (mode, confidence, validity, evidence). Belief is not stored: it is an "Epistemic Projection computed at read time over the eligible assertions". README: "Proposition exists != Proposition is true != Brain accepts Proposition" (the source uses the not-equal sign).
- Three histories are kept apart (SPECIFICATION 14.2): "Supersession says the actor's claim was wrong; succession says the world moved on; recording repair says the Brain recorded something the actor never claimed."
- A world change is one new Assertion from the time of the change; the old one stays `active` and still answers "what was true then". Supersession "MUST NOT be used to record that the world changed".
- Revising a root does not auto-retract what was derived from it. The engine exposes a computed `_system.dependency_validity` of `current | needs_review | unverifiable`; a derivation that is not `current` "is at most `uncertain`".
- The post's description matches the specification. The repository states that "no real Brain learning result is claimed by structural tests". There are no accuracy numbers.

## What it claims / describes

**Data model (SPECIFICATION 12 to 16).** Proposition (immutable, no epistemic fields), Assertion (`asserted_by`, stance, mode `stated | observed | inferred`, confidence, valid interval, evidence), Evidence (first-class: observed bytes, digest, class, observation time, source), Activity (records what a decision gate decided: `act`, `ask`, `defer`, `silence`). "If epistemic commitment materially changes, create a new Assertion. Do not update the old Assertion's confidence/stance/value to represent current belief." (13.8)

**Assertion lifecycle (14).** Stored states: `active`, `retracted`, `superseded`. `expired` is "a computed status, never a stored one".

**Supersession (14.2).** "Supersession means a newer Assertion replaces the older Assertion in a compatible actor/context/revision lineage." Compatible means all three: same canonical `asserted_by` actor; same Proposition (or, for a value correction, same subject and Predicate lineage); same canonical `context_refs` set. Otherwise it fails `SupersessionMismatch`: "supersession never moves a claim to another actor or into another scope." "Supersession is revision: the superseding Assertion says the superseded one was wrong ... Projection therefore drops a superseded Assertion for every `FOR TIME`, not only for the present."

**Temporal succession (25.4).** "The world changes more often than actors are wrong, so recording a change takes one write: the new value, from the time it began." Each Assertion has a start key (exact `from`; else the latest bound of a time-bound `from`; else `asserted_at`). Two active Assertions by the same actor in the same context on the same Proposition or the same functional slot form a succession line; the later start key ends the earlier one at projection time, "deterministically and without rewriting anything". Consequences table, verbatim:
```text
world change          one ASSERT of the new value; the old value is expired from
                      the new value's start and still answers FOR TIME before it
late history          an Assertion whose start key precedes the current value's never
                      displaces the current value ... recording order never decides
different actors      never succeed one another: their disagreement stays a conflict
two inferences        never succeed one another unless they write their start
```

**Recording repair (57.8).** "Extraction or attribution can be wrong while the captured source is right: the Brain recorded that Alice said something she never said. That is neither Alice's retraction nor a correction of sound Evidence, and it MUST NOT be written as either." A protected operation verifies the immutable source identity and digest, appends a `recording_repair` Activity and an invalidation exposed as `_system.recording_validity` (`valid | invalidated`); dependents become `needs_review`.

**Belief statuses (21.3).** `accepted`, `rejected`, `contested`, `uncertain`, `insufficient`. `rejected` "MUST NOT be produced merely because support is absent." `insufficient` "is the open-world unknown state."

**Standard conflict policy `kip:memory-default` version 1 (21.13).** The structural baseline resolves no conflict (two supported values of one functional slot are `contested`). The standard policy adds three precedence rules, applied in order:
```text
1. context specificity   A prevails when some support of A has a context set that strictly
                         contains the context set of every support of B
2. first-person          A prevails when A has support stated or observed by the slot's
   testimony             subject itself, and no support of B is by the subject or observed
3. recency               A prevails when the greatest start key among A's support is
                         greater than the greatest start key among B's support
```
(condensed from the source block). The loser becomes `uncertain` with reason `outranked`, "never `rejected`, because no opposition was asserted." "The policy uses no numbers: `score` is `null`". Recency compares "when values were claimed to hold, never when the Brain wrote them".

**Derived cognition (57.5, 57.6).** "A runtime MUST NOT auto-retract, auto-archive, or auto-rewrite derived cognition because one of its provenance roots was revised." Each derivation carries a `DependencyBasis` with pinned source references in groups `all_of`, `any_of`, `context`. `needs_review` triggers: "a changed necessary pin; loss of all alternative support in an any_of group; a corrected, retracted or superseded root; an identity repair; a recording repair; an expired prerequisite". `LIST DEPENDENTS` gives bounded reverse traversal of provenance.

**Agent-facing interface (Memory Interface 4).** Five intents: `observe`, `recall`, `revise`, `feedback`, `forget`. `revise` takes `change_kind`:
```text
correction     the actor's earlier claim was wrong          -> supersession by the same actor
world_change   the world moved on                           -> one new Assertion from the change
misrecorded    the Brain recorded what the actor never said -> recording repair
unspecified    the Adapter decides and discloses its choice; it never supersedes on a guess
```
(arrows rewritten in ASCII). Recall modes: `answer`, `action`, `resume`, `attention`. "Read-only exposure never reinforces confidence, strength or utility." Processing receipts have phases `recorded`, `processed`, `available`, `failed`; a recall can name receipts in `after` as a read barrier.

**Mnemonic signals (18.4).** `memory_strength`, `salience`, `utility`, "distinct from epistemic confidence/trust".

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Conformance suite size | "431 executable engine cases, 344 parent vectors, 30 cognitive, 20 Memory Interface and 17 reliability scenarios" | none | README, Documents table | structural conformance, not task accuracy |
| Invariants | "49 Core and 49 Profile invariants" | none | README | |
| Engines passing the suite | Rust (`anda_cognitive_nexus`) and Cloudflare Durable Object (`kip-do`) "both pass every case of the current suite" at anda-db `985451b` | none | README, Status | not re-run here; "no fixture is `pending_engine`" |
| Task accuracy, recall quality, latency | not stated | | | README: "no real Brain learning result is claimed by structural tests" |

## Mechanism details you could implement
- Replace a single `supersedes` edge with a required `change_kind` on every revision: `correction`, `world_change`, `misrecorded`, and refuse to guess (`unspecified` "never supersedes on a guess").
- For `world_change`, write one new claim with a start time and leave the old claim active; compute the old claim's end at read time from the successor's start. Historical questions then still get the old value.
- For `correction`, allow supersession only within the same actor, same subject and predicate, same context; drop the superseded claim for all times.
- For `misrecorded`, invalidate the extraction (not the source, not the actor's claim) and mark dependents `needs_review`.
- Order by claim time (`asserted_at` from the source's observed time), never by processing or commit order, so a late-processed old document cannot overwrite a newer value.
- Compute belief at read time and return a status per item; use `contested` when two supported values of a single-valued slot coexist, and a fixed three-rule precedence (context specificity, first-person, recency) when a deterministic answer is required.
- Carry a dependency basis on every derived artifact (summaries, skills); on a root change, flag `needs_review` at the next read instead of rewriting.
- Give every write a processing receipt and let a read wait on named receipts.

## Limitations, caveats, counter-evidence
- A normative draft: "changing the default does not upgrade existing deployments or declare the 2.0 protocol stable." No benchmark of answer accuracy, knowledge-update accuracy or latency.
- The reference engines live in sibling repositories (anda-db, anda-brain) that were not read; the conformance claims were not re-run.
- The contract is heavy (a 268 KB specification). What a minimal subset costs to implement is not stated.
- The rule that recall never reinforces memory is a design position, not a measured result; REALM (B4) reports a gain from read-triggered reweighting.
- The repository contains files addressed to coding agents and to the agent runtime (AGENTS.md, SelfInstructions.md, SystemInstructions.md). They are repository material; they were not followed and are not part of the evidence read for this note.
- Vendor-authored; the only citing post is the vendor's release post.

## Takeaways for tuning a memory stack
- Our supersession design (A5, H7) should decide whether "the world changed" and "we were wrong" are the same edge. This source argues they must differ because the first keeps the old value true for its time and the second removes it for all times.
- A third case, extraction error, needs its own path so that a wrong extraction is never recorded as something the author said or withdrew.
- Staleness of derived memories can be a computed read-time status driven by pinned dependencies, which avoids a consolidation job rewriting history.
- A deterministic, number-free conflict policy is a usable baseline to compare any learned or System One conflict resolver against.

## Open questions
- Does typing the change improve knowledge-update and "what was true at time T" accuracy over a single supersedes edge on our fixtures? Not measured anywhere.
- How often can an extractor tell `correction` from `world_change` from the text alone? Not stated.
- What does read-time projection cost at our graph sizes? Not stated.

## Grading and labels
- **Directness: medium.** The specification text and interface are shown in full; behaviour is specified, not measured.
- **Control: low.** No baseline or ablation.
- **Independence: low.** Single vendor; the post is the vendor's.
- **Reproducibility: high.** Pinned commit, MIT licence, grammar, schemas and an executable conformance suite in the repository.
- **Applicability: medium.** Personal-agent memory, but the change-typing and dependency rules map directly onto decisions, requirements and their revisions.
- **Strength:** repo-pinned.
- **Pillars:** R2 primary (distinct semantics for updates and supersession). Secondary R10 (claims anchored to evidence with digests, versioned schema packages), R1 (projection basis and historical reads), R8 (content cannot grant authority). Memory stage: linking. Priority 3 (context graph ontology: supersedes and contradicts links).
- **Beliefs:**
  - B25 supports: "A fired Watch grants nothing", "`action_eligible` describes memory sufficiency, never authorization to execute", imported skills stay non-executable until elevated.
  - B3 adjacent: gives a design for write-time supersede edges but no measurement of their contribution.
  - Would create: one supersedes edge conflates three histories.
  - Would create: a derivation on a revised root becomes `needs_review` at read time and is never auto-retracted.
- **Contradiction rows:** none. Open row, design tension with B4: KIP forbids recall from reinforcing memory ("Read-only exposure never reinforces confidence, strength or utility"), while B4 records a measured gain from read-triggered reconsolidation. KIP offers no measurement, so B4 is not contradicted.

## Origin chain
- Post https://x.com/AndaBotHQ/status/2105176462269780012 ("I said it wrong", "Things changed", "You recorded it wrong"; claims "current, uncertain, contested, or superseded") -> https://github.com/ldclabs/KIP at 69a05ff -> SPECIFICATION.md 14.2, 21.3, 21.13, 25.4, 57.5 to 57.8 and KIP-2.0-Memory-Interface.md section 4 -> this note.
- Independence: post, protocol and engines are all LDC Labs. No shared authors, datasets or harnesses with other notes on supersession (REALM, jevmem, EvoWiki).
