# Composition substrate implementation review

2026-10-07. Scope: first #35/#42 pure composition substrate, against the adjacent composition-boundary design review. No services, cloud, credentials, or runtime-optional completion claims. Review run: `20261007-local-astra-composition-review-01`, registered before execution.

## Verdict

**Initial verdict: changes requested for two public resolver invariants. See the remediation recheck below for the current disposition.** The normal loader protects built-in files and supplies mandatory core, so the ownership finding is not an demonstrated loader-based manifest exploit. Both findings concern `resolve_bundle`'s advertised validation/value-snapshot contract and are addressable within this substrate. Deferred worker prompts/output, API/retrieval enforcement, tenant routing and cloud evidence are not findings against this slice.

## Findings

1. **P2 — Derive identity and vocabulary from the same freshly validated snapshot.** `src/context_graph/domain/pack_bundle.py:118` uses the input registry's cached `version`, while line 130 serializes its current mutable Pack contents; lines 127–129 independently copy mutable composed dictionaries. A caller can mutate nested manifest collections between registry construction and resolution. Adding `core.events['tool.review_probe'] = EventDef()` preserves the old bundle identity even though the reconstructed registry has a different schema version. The probe observed `schema_version=sha256:7aa9c7d4db1d5a24`, reconstructed version `sha256:c7592128c794e4d9`, and identical before/after bundle identities. Mutating only composed dictionaries likewise can separate allowed vocabulary from the reconstructed schema. Fix by snapshotting manifests and rebuilding/validating a private registry before deriving processing, identity, vocabulary and snapshots; alternatively reject inconsistent inputs. Add regression coverage for pre-resolution manifest and composed-dictionary mutations. The existing post-resolution mutation test does not cover this.

2. **P2 — Validate required schema ownership, not only global names.** `src/context_graph/domain/pack_bundle.py:111` accepts required node names from any pack. A valid direct registry containing an empty `core` pack and `lab`-owned `Event`, `Entity`, `Summary` (each only having an `id` field) receives all five core handler bindings. The manifest-level enabled-handler owner check at line 94 does not protect these implicit bindings. Existing OntologyRegistry validation correctly rejects a wholly absent core, but existence alone is insufficient. Require prerequisite types to belong to their engine-designated schema owner, including cross-pack prerequisites of user extraction, and document/check any specialized required schema shape. Preserve direct schema construction separately from executable bundle acceptance. Add negative tests for foreign-owned prerequisite names.

## Verification and remaining assessment

Independent command: `PYTHONPATH=src /private/tmp/engram-ontology-review-venv/bin/python -m pytest tests/unit/test_pack_composition.py -m 'not integration' -q` — **21 passed**. Raw outputs: `runs/20261007-local-astra-composition-review-01/tests.txt`, `probes.txt`, `ownership-probe.txt`. An initial absent-core probe was rejected by existing registry validation, correctly; the adjusted ownership probe reproduced finding 2.

Inspection found explicit-empty versus default optional roots, dependency closure, built-in shadow protection, exact handler ID parsing, requirement-without-enablement semantics, immutable post-resolution values, legacy empty-processing canonical serialization, and processing addition/removal classification consistent with this slice's stated contract. No additional blocker identified there. Tests are local substrate evidence only. This report records the initial reviewed implementation; remediation needs a separately tracked recheck.

## Remediation recheck

2026-10-07, read-only implementation inspection; no additional test execution by this reviewer. **Current verdict: approve the pure composition substrate; both reported findings are resolved.**

- Finding 1 resolved at `pack_bundle.py:85`: canonical manifest snapshots are captured first, then parsed and recomposed into a fresh private registry. Identity, processing and vocabulary now derive from that registry, and reconstruction uses the retained snapshots. Stale input dictionaries and cached versions no longer supply the bundle's values. The new pre-resolution event-mutation regression checks changed identity and matching reconstructed schema version.
- Finding 2 resolved at `pack_bundle.py:121`: each required node type must have its designated owner; the handler owner is the default, with explicit core ownership for user extraction's Event/Entity prerequisites. The new foreign-owned core-types regression exercises the reported bypass. This closes the ownership finding; it does not claim arbitrary handcrafted built-in manifests are authenticated against engine field-level schemas. Built-in file shadow protection remains the configured loader's protection.

Inspected recorded evidence: `runs/20261007-local-composition-recheck-03/tests.txt` reports **23 passed**. Its manifest identifies the local resolver recheck. Earlier recheck-01/-02 malformed-fixture failures remain historical attempts and are not relabeled as successful evidence. Worker output/prompt policy, API/retrieval gates, tenant routing and Spanner acceptance remain outside this approval.
