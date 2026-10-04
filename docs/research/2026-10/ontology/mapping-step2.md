# PDLC pack: mapping real projects (step 2)

**Date:** 2026-10-04
**Samples:** Apache OpenDAL (88 RFCs, 3 living specs, last 400 commits, changelog, CODEOWNERS), Apache Kafka (last 400 commits), GitLab's public production tracker `gitlab-com/gl-infra/production` (15 closed incidents, 10 change issues, their links and related merge requests).
**Result:** pack v0.4 (17 node types, 25 edges); all 30 competency questions still covered; every type and edge needed by at least one question.

## Access limits, stated first

From this session, git history and GitLab's API were reachable. GitHub's issue and pull-request pages and API, Apache's Jira, and Apache's wiki (Kafka's KIPs) were not. So:
- For OpenDAL and Kafka, everything below is what **git itself** declares: commit messages, trailers, changed files, documents in the repository. Anything recorded only on a PR page or in Jira (PR descriptions, linked issues, review states, CI runs, Jira fields and links) was not visible and is reported as "not measured", not as absent.
- Samples are small (400 commits each covers about 4 months of OpenDAL and 2 months of Kafka; 15 incidents). Percentages are indicative.

## What each source declares

| Signal | OpenDAL (400 commits) | Kafka (400 commits) | GitLab (15 incidents) |
|---|---|---|---|
| PR number in the commit | 99% | 99% | n/a |
| Ticket the change implements | 3% (GitHub issue in message) | 62% (Jira key in subject) | n/a |
| Explicit "no ticket" convention | none | 39% (`MINOR:` prefix) | n/a |
| Change type and scope (`fix(services/s3):`) | 96% | Jira key instead | n/a |
| Reviewers named | not in git (PR page) | 96% (`Reviewers:` trailer) | n/a |
| Tests changed in the same commit | 14% | 74% | n/a |
| Design document cited (RFC / KIP) | 2% | 10% | n/a |
| Reverts | 1% | 0.2% | n/a |
| Severity and status | n/a | n/a | 100% (labels) |
| Affected service | n/a | n/a | title only (no label) |
| Root cause recorded | n/a | n/a | 13% (label) |
| Linked change issue | n/a | n/a | 0% |
| Related merge request | n/a | n/a | 33% |

Plus, for OpenDAL: all 88 RFCs carry a name, start date and RFC PR; 79 carry a real tracking issue; 17 cite earlier RFCs. The changelog lists 3,129 PR links across 154 releases, grouped as breaking, added, fixed, docs and CI. CODEOWNERS maps 8 paths to people.

## Type by type

| Type | Fed by the samples? | Evidence | Verdict |
|---|---|---|---|
| Change | yes, all three | PR numbers, files, scopes | solid |
| Decision | yes | 88 OpenDAL RFCs with dates, PRs, tracking issues | solid |
| Spec | yes | OpenDAL `docs/specs/` (3 living contracts); Kafka KIPs cited by 10% of commits | solid, small |
| Component (was Service) | yes | OpenDAL: 66 service modules via paths and commit scopes; Kafka: modules by directory; GitLab: service named in incident titles | **renamed**, see below |
| Release | yes | OpenDAL changelog: 154 releases, 3,129 PR links | **added**, see below |
| WorkItem | partly | Kafka Jira keys (62% of commits); GitLab change issues; OpenDAL issues behind the API | solid where declared |
| Review | partly | Kafka reviewer trailers (96%); OpenDAL not visible | depends on source |
| Incident | yes | GitLab: severity and status on all 15 | solid |
| TestCase | yes | test files; OpenDAL behaviour tests | solid |
| Requirement | weakly | OpenDAL spec sections; no explicit requirement ids anywhere | key by document + section |
| Request | weakly | OpenDAL tracking issues (behind the API) | not measured |
| Constraint | no structured source | would come from extraction ("must" statements in specs) | extraction only |
| DesignElement | overlaps Decision | an OpenDAL RFC is design and decision in one document | keep; one document can be both |
| TestRun | no | needs the CI system's API | not measured |
| Deployment | no | GitLab mentions deploys only in prose (5 of 15) | **unchecked against real data** |
| Team | no | CODEOWNERS names people, not teams | weakest type; keep, low priority |
| Lesson | no | GitLab incidents had no corrective actions in the description | extraction only |

## What changed in the pack (v0.3 → v0.4)

1. **Service became Component**, with a `kind` (service, library module, binding, website). OpenDAL and Kafka have modules, not running services. Backstage already calls this a Component. Deployments still target components of kind `service`.
2. **Release added**, with `INCLUDES` Release → Change taken from changelogs. For a library, "has it shipped?" means "which release included it", not which deployment.
3. **AMENDS added** between decisions (builds on, updates, replaces part). OpenDAL's 17 cross-citing RFCs change earlier RFCs in part; none uses "supersedes". `SUPERSEDES` stays for whole replacement.
4. **The `status` question prefers the Spec.** OpenDAL states it explicitly: RFCs are immutable history; specs hold the current contract, "even when a newer RFC changes the accepted design". The current answer comes from the Spec, with decisions as the history behind it.
5. **Tests verify Specs.** OpenDAL's behaviour tests are its declared conformance suite for the specs, so `VERIFIES` can now point at a Spec.
6. **"No ticket" is a convention, not a gap.** Kafka marks 39% of changes `MINOR:` on purpose. `Change.ticket_exempt` stops "changes without a ticket" from flagging them.
7. **Git-only rule added** (`pdlc.change.committed`). It reads the PR number, type and scope, Jira keys and reviewer trailers straight from commit messages, for when no PR webhook is available.
8. **Weak links are proposals.**
   - Test files changed in the same commit propose `VERIFIES` at confidence 0.3.
   - Incident → service (title only) and incident → merge request (fix or cause, unclear) are proposed links, not facts.
9. **Planned production changes** (GitLab change issues with a criticality level) are WorkItems of kind `production_change`. Incidents can be attributed to them as well as to code changes.

## What this means for the build

- **The GitHub adapter must read PR pages, not just commits.** For OpenDAL the ticket a change implements is in git only 3% of the time. It lives in the PR's description and linked issues, which the webhook carries. A git-only import would leave most "implements" links missing.
- **Each source has its own conventions,** like Kafka's `MINOR:` and `Reviewers:` and OpenDAL's conventional commits. These belong in per-source settings of the adapter, not in the ontology.
- **Incidents are the weakest-linked part.** Severity and status are always there. Which service, which change caused it, and what was learned almost never are. Questions CQ14, CQ20, CQ21 and CQ25 will depend on inferred links and their confidence (the R10 link-scoring work).
- **Deployment, TestRun and Lesson remain unchecked against real data.** They need a CD system, a CI system and postmortems. None was reachable.

## Next

Step 3: freeze pack v1.0 from v0.4 and write the one-page summary for sign-off (final types, what changed since v0.1 and why).
