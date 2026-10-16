# One branch for Engram work

Use **`feature/engram-memory-episodes`**. Its name comes from an earlier slice; it is now the canonical branch for the complete Engram work, including foundation, goals, projection changes, pilot, guide and supporting research. No second branch is needed to assemble the application.

The 16 October reconciliation covers available local and fetched remote history since **25 September 2026**, plus versionable uncommitted files in the repository's worktrees. The [machine-readable audit](branch-lineage-2026-10-16.json) records exact tips, ancestry, file hashes, source locations and recovery destinations.

| Work | Disposition on the canonical branch |
|---|---|
| Walkthrough, foundation snapshot, verified foundation, G06, G07 and Memory/pilot work | Already included by ancestry; later corrections retained |
| Older primary worktree | All 1,884 real versionable files accounted for: 1,837 match current content; 47 exact older contents exist in branch history |
| September architecture/gap review and system-map documentation | Merged into this branch |
| Research bus, execution harness and labelling history | Merged and preserved as research; not claimed as verified pilot behavior |
| Pending-drain fix and idle projection flushing | Earlier behavior already present with newer worker safeguards; original lineage recorded without rolling back newer code |
| G07 conformance and rollback checkpoint work | Equivalent/superseded patches recorded; newer date validation and commit-without-PR protection retained |
| Uncommitted worktree files absent from this branch | 368 files recovered with SHA-256/source-path records: historical G07 evidence and presentation material, research queue updates, and labelling inputs/results |

All **27 distinct recent branch tips** in the audited set are ancestors after reconciliation. Multiple names referring to the same tip are recorded as aliases. Old branch names remain historical references and existing worktree handles; they are not additional delivery branches and were not deleted.

Three older foundation status/index files were preserved under `docs/review/spanner-compatibility/lineage-archive/foundation-gate-20261009/` instead of replacing the current status. Original source worktrees were not modified. Local virtual environments, ignored credentials and machine-only caches are not deliverables.

The reconciliation changed documentation/research/harness content, not the running pilot's source files. Every source hash recorded by continuation02 still matched at that reconciliation checkpoint, before the subsequent separately recorded HTTP-client adjustment. The pending-consumer and PDLC contract/pack checks passed **138 tests**. Research harness inclusion is preservation, not a new execution or validity claim.

The pilot has its own verification verdict. Consolidating Git history does not turn a failed or in-progress run into a pass. See [team walkthrough](team-walkthrough.md) for reproduction prerequisites and evidence limits.
