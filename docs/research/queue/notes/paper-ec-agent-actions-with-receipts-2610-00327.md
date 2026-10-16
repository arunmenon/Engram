---
schema_version: 1
artifact_id: N-SURVEY-20261005-02
artifact_type: note
producer: triage
run_id: survey-20261005T054504Z-d350
created_at: 2026-10-05T06:30:00Z
idempotency_key: note:survey:arxiv:2610.00327
input_refs: []
pillar_primary: R1
pillar_secondary: [R8]
memory_stage: none
beliefs_affected:
  supports: [B1]
  contradicts: []
evidence:
  directness: 4
  control: 3
  independence: 2
  reproducibility: 3
  applicability: 2
evidence_scale: 1 (weak) to 5 (strong), per dimension
source_url: https://arxiv.org/abs/2610.00327
found_via: survey
---

# Actions with Receipts: Jointly Binding Claims, Evidence, and Execution for Replayable Tool-Agent Auditing (EC-Agent)

- **URL:** https://arxiv.org/abs/2610.00327 (read via https://arxiv.org/html/2610.00327, v1)
- **Type:** paper
- **Author / org:** not stated in the extracted text
- **Date:** v1 dated 29 September 2026
- **Retrieved:** 2026-10-05
- **Cited by evidence:** survey query for B1/B2 (served-artifact retention, replay)
- **Relevance to a memory stack:** high for R1. It is the closest published design to our receipt idea and it states plainly that its replay checks hashes and quotes, not source bytes.

## TL;DR
- A receipt binds four things: the emitted claim (event index, field, substring offsets, SHA-256), the source span (document id, span id, offsets, UTF-8 hash, exact quote), an execution digest over the ordered event prefix, and a joint digest over all of these plus manifest identity.
- Substitution detection: "1,275 of 1,280 cross-object attacks (0.9961)" with false rejection 0.0031.
- Overhead is tiny: serialization 0.19 ms, verification 0.47 ms, bundle replay 1.31 ms, +3.0 declared tokens per receipt; a full execution rerun costs 16.88 s.
- Replay "assumes that snapshot remains available": the verifier "re-reads the immutable span and checks its SHA-256 digest ... and, when present, an exact quote". If the source document is gone, only the quoted span survives; the full served context cannot be reconstructed.
- Dynamic stressors: "0.9947 stale rejection, 0.9896 unauthorized-span rejection, 0.9078 injection resistance, 0.8892 conflict resolution, and 0.8127 perturbed-task success".

## What it claims / describes
Receipt tuple (c, rho_c, R_c, D_exec, D_joint). Bundle replay reloads the saved receipt, trace, corpus manifest and verifier result, reconstructs the claim substring from committed offsets, recomputes the canonical event digest and the joint commitment, and re-verifies without re-running the policy. Execution rerun is a separate, expensive third check comparing deterministic aggregate trace digests. Dynamic evaluation substitutes document versions and revokes access after commit and checks that replay rejects stale documents and unauthorised spans.

## Numbers

| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| cross-object substitution detection | 0.9961 (1,275/1,280) | ablations 0.0156 to 0.0625 per removed property | attack suite | |
| false rejection | 0.0031 | | | |
| semantic support precision / F1 / false accept | 0.9213 / 0.8865 / 0.0729 | lexical, NLI baselines (numbers not extracted) | 384-pair split, conflict-aware guard | annotator kappa 0.834 |
| agent task success | 0.7278 | not stated | three-seed aggregate | agent LLM not named |
| semantic F1 (agent) | 0.8721 | | | |
| joint replay | 0.9976 | | | |
| calls / latency per task | 5.46 / 16.31 s | | | |
| serialization / verification / bundle replay | 0.19 / 0.47 / 1.31 ms | matched control | | |
| execution rerun | 16.88 s | | | |
| token overhead | +3.0 declared tokens per receipt | | | |
| dynamic: stale rejection | 0.9947 | | Section 4.7; denominators in App. D.12 (not extracted) | |
| dynamic: unauthorized-span rejection | 0.9896 | | | |
| dynamic: injection resistance | 0.9078 | | | |
| dynamic: conflict resolution | 0.8892 | | | |
| dynamic: perturbed-task success | 0.8127 | | | |
| fixed corpus | 128 HotpotQA dev-distractor records | | | not engineering work |

Agent model and "frozen language-model judge" checkpoint: not stated in the text read, so judge and system may share a model (unknown).

## Mechanism details you could implement
- Bind the source span by (doc id, span id, char offsets, UTF-8 SHA-256, exact quote), and bind the claim by (event index, field, offsets, hash). Domain-separated digest over canonical JSON of the ordered event prefix.
- Two replay tiers: cheap bundle replay (ms) for every review; expensive execution rerun (seconds) only on dispute.
- Record version and access-state identity in the receipt so replay can return "stale" or "unauthorised" instead of silently serving current content (matches P0 step 3).

## Limitations, caveats, counter-evidence
- Trusted runner, logger, manifest, verifier and replay environment are assumed; "Observation authenticity remains an external property".
- Only quoted spans plus hashes persist; the rest of the served context is recoverable only if the snapshot is still available. This is the L1-versus-L2 distinction in P0 step 4.
- Small fixed corpus (128 records), QA not build-time engineering.
- Code "in the Supplementary Material"; no public repository URL found.

## Takeaways for tuning a memory stack
- Supports B1: hash-and-quote receipts prove integrity but do not let a reviewer read what was served once the source changes or disappears; retention (or native source versioning) is still needed for reproduction.
- Budget for receipts is negligible (sub-millisecond, ~3 tokens); the cost question is storage of retained content, which the paper does not measure.
- Adopt "stale" and "unauthorised" as explicit replay outcomes.

## Open questions
- Appendix D.12 denominators for the dynamic stressors.
- Storage cost if full served spans (not just quotes) were retained.
