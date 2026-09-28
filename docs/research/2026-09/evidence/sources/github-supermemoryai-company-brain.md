---
schema_version: 1
artifact_id: N-20260927-11
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103668051468300701", "file_id": null, "sha256": null}, {"artifact_id": "post:2103668253688226271", "file_id": null, "sha256": null}, {"artifact_id": "post:2103668795843973538", "file_id": null, "sha256": null}, {"artifact_id": "post:2103727822879719832", "file_id": null, "sha256": null}, {"artifact_id": "post:2103710768588083240", "file_id": null, "sha256": null}, {"artifact_id": "post:2103668797832098090", "file_id": null, "sha256": null}, {"artifact_id": "post:2103915218036539456", "file_id": null, "sha256": null}, {"artifact_id": "post:2103836234540011899", "file_id": null, "sha256": null}, {"artifact_id": "post:2103854376649662622", "file_id": null, "sha256": null}, {"artifact_id": "post:2103825222210052307", "file_id": null, "sha256": null}, {"artifact_id": "post:2103794404657950969", "file_id": null, "sha256": null}, {"artifact_id": "post:2103854715641442598", "file_id": null, "sha256": null}, {"artifact_id": "post:2103856019843760247", "file_id": null, "sha256": null}, {"artifact_id": "post:2103807744688189763", "file_id": null, "sha256": null}, {"artifact_id": "post:2103891294296891555", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:supermemoryai/company-brain
claim_cluster: github:supermemoryai/company-brain
feeds: ["memory"]
primary_source: https://github.com/supermemoryai/company-brain
source_commit: d76cc1c9cc4fbddaf95f3a560edcaa04001c4dee
strength: repo-pinned
pillar_primary: R8
pillar_secondary: ["R7", "R2"]
tags: {"mechanism": ["permission-scoped memory containers", "write-narrow read-wide scoping", "asker-access reads", "per-request tool leasing with approval", "personal-only writes"], "workload": ["multi-user Slack agent", "team knowledge"], "lifecycle_stage": ["write", "read", "governance"], "cross_cutting": ["shared_state"]}
evidence_grade: {"directness": "high for the design: documented scoping rules and container tags in a pinned repo", "control": "unknown: no measurements of leakage, recall or quality", "independence": "low: vendor documentation of its own product", "reproducibility": "medium: open source at a pinned commit (Apache-2.0), but memory runs on the hosted supermemory API", "applicability": "high: multi-user, permission-aware memory for a team agent is our shared_state problem"}
beliefs_affected: {"supports": ["B25"], "contradicts": [], "would_create": ["A shipped multi-user agent memory writes each message to exactly one scope (person, private channel, or org) and reads only with the asker's access; no measurements published"]}
claim_correction: posts call it "fully Open source" and "frontier memory"; the repo requires a hosted supermemory API key for the memory layer (the author confirms in 2103854376649662622; a self-hosted supermemory or another provider is possible per 2103915218036539456), and no memory quality numbers are published
---

# Company Brain: open-sourced multi-player Slack agent with permission-scoped memory (supermemoryai/company-brain)

- **URL:** https://github.com/supermemoryai/company-brain
- **Type:** repo
- **Author / org:** supermemory (Dhravya Shah); Apache-2.0; TypeScript on Cloudflare Workers, Durable Objects and D1, memory on supermemory
- **Date:** open-sourced 2026-09-26 (product previously discontinued, per README)
- **Retrieved:** 2026-09-27, commit `d76cc1c9cc4fbddaf95f3a560edcaa04001c4dee` (2026-09-26 12:42:20 -0700, "Merge pull request #12 from mvanhorn/export-memories-markdown"); local copy repos/company-brain. Read: README.md, docs/guide/permissions.md. The linked X article (x-article:2103652547227750400) was not fetchable.
- **Cited by evidence:** @dhravyashah https://x.com/dhravyashah/status/2103668051468300701 , https://x.com/dhravyashah/status/2103668253688226271 ; @supermemory https://x.com/supermemory/status/2103668795843973538 ; replies raising permissions questions: @gatedsh https://x.com/gatedsh/status/2103856019843760247 , @kemalegebuilds https://x.com/kemalegebuilds/status/2103891294296891555 ; other posts listed in input_refs
- **Relevance to a memory stack:** high for R8 and shared_state. A shipped, readable reference design for permission-scoped memory in a multi-user agent, with concrete scope tags and tool-access rules. No quality or leakage measurements.

## TL;DR
- Three memories: employee memory (one per person, from DMs), private-channel memory (one per private channel), public-channel memory (one per org). "A message writes to exactly one of these, whichever room it happened in."
- Reads widen with privacy: public channel reads org memory; private channel reads its own + org; a DM reads your employee memory + org + every private channel you belong to. "The bot only ever reads with the asker's own access."
- Tools: reads use your personal connection if any, else the org-shared one; writes only through your personal connection; org-shared connections are read-only for everyone including admins.
- Leasing: a request needing a teammate's personal tool posts an approve/deny card; grant lasts 10 minutes; unanswered request expires after 15; some tools (Gmail) cannot be leased.
- No numbers: nothing on recall quality, leakage tests, or how permission changes propagate to stored memories.

## What it claims / describes
- Container tags (permissions.md): `sm_org_shared` for public channel memory, `slack_channel_<channel id>` per private channel, `user_<user id>` per person, all inside the deployment's supermemory account.
- "If you're not in a private channel, its memory doesn't exist for you, not even by inference in a DM."
- Answers cite which memory an answer came from (example in permissions.md).
- The Graph page shows public memory plus your own employee memory, never a teammate's.
- Roles: owner, admin, member stored in the D1 `member` table; no UI to promote admins yet.
- Proactivity: the bot "speaks up" in conversations; org-wide and per-channel chattiness settings.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| tool lease duration | 10 minutes | | permissions.md | design parameter |
| unanswered lease expiry | 15 minutes | | permissions.md | design parameter |
| memory quality / leakage | not stated | | | no evaluation published |

## Mechanism details you could implement
- Write every observation to the narrowest scope it arose in; compute the read set at query time from the asker's memberships (union of personal + member private scopes + org), never from the bot's own access.
- Represent scopes as container tags on one store (`user_<id>`, `slack_channel_<id>`, `sm_org_shared`) so retrieval filters are simple and auditable.
- Attribute every write action to a real person's connection; keep shared connections read-only.
- Short-lived, per-request, explicitly approved access grants for borrowed capabilities.
- (inference) Pair this with per-answer source citation so a reviewer can check which scope contributed (R1).

## Limitations, caveats, counter-evidence
- No measurement of cross-scope leakage, recall, or answer quality.
- Not stated: what happens to memories when a user leaves a private channel or permissions change (the question @gatedsh asks in reply 2103856019843760247); whether consolidated or derived memories inherit the narrowest scope of their sources.
- Memory runs on the hosted supermemory API unless replaced; "open source" covers the harness.
- Admin promotion requires editing the database.

## Takeaways for tuning a memory stack
- For multi-agent or multi-user shared state, make scope a write-time field and access a read-time computation; the Scope Before You Persist paper (N-20260927-02) gives the quality reason for scoping learned rules, this repo gives the permissions reason for scoping facts.
- Add explicit tests for derived memories: a summary built from a private channel must not surface in a public channel (inference; untested here).

## Open questions
- Permission revocation: are stored memories re-scoped or deleted?
- How are consolidated "memories formed" (supermemory's consolidation phase, see catalogue note consolidation-phase-supermemory-rauch.md) scoped when sources span scopes?

## Grading and labels
- Directness high (design is documented); control unknown; independence low; reproducibility medium; applicability high.
- Pillars: R8 primary (permissions, execution authority, review ownership); R7 secondary (interface contract for a shared memory layer); R2 secondary (write-time scope assignment).
- B25 supports: tool access requires explicit human approval per request; nothing is granted by content.
- Would create: shipped design reads only with the asker's access and writes to exactly one scope (unmeasured).
- Tags: shared_state.
- No contradiction rows.

## Origin chain
posts 2103668051468300701, 2103668253688226271 (@dhravyashah), 2103668795843973538 (@supermemory) -> github.com/supermemoryai/company-brain at d76cc1c9 -> README "Private by design"; docs/guide/permissions.md sections "Three memories", "What a conversation can read", "Tool access", "Leasing" -> this note. The X article with the architecture write-up was not fetchable. Independence: vendor documentation; relates to catalogue note consolidation-phase-supermemory-rauch.md (same vendor).
