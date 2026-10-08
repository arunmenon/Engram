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
These fixture corrections and their local proof are pending final recheck.
