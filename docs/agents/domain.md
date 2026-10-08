# Domain documentation

Single-context Python repository. Keep the existing layout; no new glossary/framework is required for setup.

- Read relevant decisions under docs/adr/, especially ontology packs (0018) and backend abstraction (0019), rather than the entire directory.
- If GLOSSARY.md or GLOSSARY-MAP.md exists, use its vocabulary; otherwise proceed without creating placeholder glossaries.
- Current runtime and ontology definitions live under src/context_graph/ and src/context_graph/ontology/packs/. Inspect the code before making behavior claims.
- Goal scope, acceptance and evidence live under docs/review/spanner-compatibility/, especially goal-verification-standard.md and 2026-10-08-small-goal-inventory.md. Read only the selected goal and relevant reviews/runs.
- CLAUDE.md contains historical Redis/Neo4j architecture descriptions. They do not override the current real-Spanner experiment scope, current code or user decisions.
- Core is mandatory. Optional memory/user/domain capabilities require declared supported dependencies. Tenant-to-database authorization is distinct from pack selection and within-tenant hierarchy policy.
- Surface conflicts with existing ADRs; do not silently rewrite architecture or declare a proposal implemented.

## Using the installed skills

The local Codex installation includes implement-spec, setup-matt-pocock-skills, tdd, code-review and to-tickets. Installation is user-level; these repo configuration files travel with Git. Another machine or Claude Code web environment needs its own skill installation.

At invocation, explicitly provide docs/agents/issue-tracker.md, this file, the approved goal specification and named issue scope. The orchestrator must pass these context pointers and the goal verification standard to every implementer/reviewer.

implement-spec implements an already approved ticket graph; it must not expand to the whole umbrella. to-tickets drafts proposed slices for review and reuses existing tickets. code-review receives a fixed base commit and the selected goal/spec; it does not review unstarted goals as missing work. Prefer focused rechecks of findings instead of repeated broad review loops.
