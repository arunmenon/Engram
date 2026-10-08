## Standards

Reviewed frozen `202fb5c` against `41f6956` using `git diff 41f6956...202fb5c` and `git log 41f6956..202fb5c --oneline`. Raw evidence: `/tmp/engram-g07-standards.diff` and `/tmp/engram-g07-standards-commits.txt`.

**Documented standards:** No violations found against the supplied AGENTS cost-aware rules or the user's concise, understandable, modular/no-bloat requirement. No repository coding-standards files were identified. No cloud operations or repository edits performed.

**Heuristic findings (judgment calls, nonblocking):**

1. **P3 — Possible Repeated Switches / Shotgun Surgery:** `scripts/engram_goal03_implementation_demo.py:470` and the related changed hunks at 478, 502, 564, 644, 764, 766, 786, 825 and 1065 repeat `goal in {"G04", "G05", "G06", "G07"}`. Adding G07 requires changing the same membership decision throughout retrieval, persistence assertions and evidence freezing. A single named goal-capability predicate or immutable group would reduce the risk of the next goal missing one guard. Preserve independently scoped G06/G07 conditions; a generalized strategy framework would be unnecessary.

2. **P3 — Possible Duplicated Code:** `scripts/engram_goal07_prepare.py:15–24` and `scripts/engram_goal07_event_demo.py:16–28` duplicate argument parsing, `re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", args.run_id)`, evidence-path construction and the historical-directory rejection. Because this is the same evidence-protection policy in both entrypoints, a small shared preflight helper would keep future validation changes consistent. The distinct prepare/demo operations should remain separate.

Fixture slices intentionally keep literal expectations independent; their similar construction shapes alone do not justify introducing a shared oracle abstraction. Runtime changes remain in the pack and payload-contract owner, and retention has a focused shared module.

**Summary:** 0 documented-standard violations; 2 nonblocking heuristic observations. Worst within this axis: repeated goal-capability checks increase maintenance risk. No execution tests were needed for this read-only standards assessment.
