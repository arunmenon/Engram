# Engram replication reference — 2026-09-25

This pack compares the stale GitHub repository with the owner's newer ADR and companion LLD transcripts. The supplied transcripts take precedence where they conflict with the repository. They retain original wording, including transcription errors; file names and ambiguous dictated terms require confirmation during implementation.

## Contents

- [Staleness review](engram-staleness-review-2026-09-25.md): findings, pinned repository revisions, priorities and verification limits.
- [ADR transcripts](adr-catalog-transcripts.md): 23 complete ADRs, partial ADR-0030 and one non-ADR open issue (Artifact-0025). Duplicate introductory mentions do not count as additional ADRs.
- [Active companion LLD transcripts](lld-catalog-transcripts.md): complete companions 0001–0016 and title-only 0017. Superseded versions are excluded.
- [Review evidence](review-evidence/): seven-branch inventory, source locations, targeted test results and local contract probes.

## Interpretation

Accepted design, implemented functionality and production acceptance are distinct. Several supplied decisions remain proposed, partial or gated. The review establishes gaps in the shared repository; it does not certify the newer source implementation. The reference collection is still incomplete.

The report examined main at `f641a0f96c39f0808d5e017e915bb9e3d5187394` and dev at `a1aed9b3c078955eb6433618d0f0c1d98e0e120d`. The latest inspected evaluation branch was `9df84ed7cb211aba42c8f287c7c52145931f7ce1`.

## Verification evidence

Targeted tests on dev with Python 3.12: **197 passed, 13 skipped**. See the report for the exact coverage and exclusions. These are historical results from the pinned dev revision, not tests of this documentation branch's main-based application snapshot.

`review-evidence/contract-probes.py` can be run in an environment containing that pinned dev package. It uses local function calls and a simulated model failure; it does not call live database or model services. The JSON file preserves its result. The simulated exception's terminal traceback was omitted from this publication; the test log omits the local interpreter path.

This branch adds documentation and review evidence only. Implementation should follow the completed reference and explicit acceptance fixtures.
