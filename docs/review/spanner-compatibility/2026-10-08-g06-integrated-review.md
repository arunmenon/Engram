# G06 integrated implementation review

Reviewed range: `9914921...d93331d`. Scope: approved G06 tickets #51–#53;
the three local evidence documents and G06 ticket draft are the acceptance sources.
This review does not claim real-Spanner journey acceptance.

## Spec — Astra

The independent review found no concrete implementation/spec blocker. Incident
identity and deployment lookup include repository/service and the event-time
cutoff. Remediation declarations do not resolve incidents or infer cause.
Authored Lesson identities are separated from inferred lessons, remain tentative,
and retain declaration evidence. Explicit typed citations name exact lessons from
exact Spec revisions. Unknown references use documented reference stubs; rejected
support has a retrieval regression. Bounded string-pattern validation is generic,
with no PDLC-specific engine dispatcher.

Outstanding acceptance: actual HTTP retry/conflict/no-write behavior, ordinary
workers, integrated retrieval on Spanner, and retained-G05 protection during the
journey. Local tests alone do not close the tickets.

## Standards

The independent standards review found no documented code-standard blocker.
It identified stale pack-authoring documentation saying regex was unsupported;
`106f177` corrects this to the supported bounded string `pattern` syntax.

Optional follow-ups: repeated goal dispatch and module-global target configuration
in the existing demo harness could be simplified in a focused cleanup. Explicit
reported/detected pack mappings are proportionate; no abstraction is needed merely
to remove that duplication. These are maintainability judgments, not passing-cloud
evidence or authorization to expand G06.

## Review execution

An initial Astra attempt hit an agent usage limit. The subsequent retry completed
and supplied the assessment above. Harness changes after `d93331d` receive their
own review before the full cloud journey. Failed preparation run
`20261008-cloud-g06-prepare-01` remains preserved; preparation retry
`20261008-cloud-g06-prepare-02` installed schema and initialized empty G06 ownership
while verifying G05 before/after fingerprints unchanged.

## Harness review findings before cloud execution

Astra identified that the stored-edge oracle could miss an unintended
`ATTRIBUTED_TO` causal relationship. `18edcb1` includes it in the exact G06
edge oracle, expecting none. Query expectations can now pin intent-specific
edge sets from frozen fixtures, because the incident intent deliberately does
not traverse `DEPLOYED_TO`; those expectations must be subsets of declared
stored edges. This does not change the retrieval questions or engine behavior.

Fixture review also required a same-repository/different-service deployment
control, independently of the different-repository control, plus candidate
absence queries for rejected inputs with computable identities. Full-table
no-write fingerprints remain required for every rejection and duplicate.
The fixture corrections passed independent recheck and all four original local
fixture tests. A subsequent driver review found reused run IDs could overwrite
retention evidence; `449ceb0` rejects unsafe/existing IDs before loading credentials.
Two additional regression tests passed. Astra cleared the corrected runner,
including the requirement for successful real pack extraction on G06 Spec events.

## First full-cloud attempt and semantic decoder correction

`20261008-cloud-g06-all-01` passed 13 checks, then stopped on the first REMEDIATES
confidence assertion. The raw SQL snapshot stores float `1.0` as
`{"$float":"1.0"}`, as designed by Engram's existing Spanner codec. The runner
incorrectly compared the encoded object directly with a semantic float. Decoding
the recorded cell through Engram's normal decoder returns exactly `1.0`.

`6126577` corrects only the stored-property comparison to use that decoder;
raw observations, exact expected values, API assertions and full no-write
fingerprints remain intact. Thirteen focused codec/fixture tests passed, and
Astra cleared the narrow correction. No engine or pack change was made after
the first cloud attempt. That failed attempt remains preserved, its workers
stopped without shutdown errors, its exact registered data was removed, and the
empty G06 owner advanced to epoch 3. G05's retention guard passed.

## Second full attempt and missing-candidate oracle correction

`20261008-cloud-g06-all-02` passed 35 checks before an absence-query assertion
failed. The rejected Lesson was absent and full-table no-write fingerprints
matched. However, the query text `absence-check-<event UUID>` matched other
artifacts containing “check.” Artifact retrieval explicitly combines seed hints
with discovery and preserves unresolved-ID fallback; an absent seed does not
make the query an ID-only lookup.

Astra classified the empty-answer expectation as oracle overreach and corrected
its earlier endorsement. `e73f100` preserves the request, requires the candidate
absent and the answer untruncated, and retains all full-table no-write assertions.
The twelve final exact journey questions/sets are unchanged. A local regression
demonstrates a missing Lesson seed discovering another matching Spec.
Astra cleared this correction before the epoch-5 full rerun. The failed attempt
restored the empty database at epoch 5 and verified G05 unchanged.

The new regression first failed because required retriever constructor settings
were missing; `fce9371` fixes only its setup. Seven journey/guard tests then
passed. This test-only correction followed the third run's source freeze and is
explicitly separate from its archived source. No runtime, pack, fixture or final
query oracle changed during that execution.
