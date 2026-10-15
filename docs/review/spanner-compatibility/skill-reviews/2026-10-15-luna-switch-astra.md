# Astra review: Luna configuration and call-ceiling removal

Independent follow-up to the authorized pilot review. Source inspection only; reviewer did not run tests or operational calls.

Verdict: no blockers in the scoped diff.

Luna request options are consistent across extraction, text generation and intent classification; explicit legacy overrides retain previous options. The artificial ceiling and CLI argument are removed, while observation still forwards actual provider responses. Tests cover all three paths, the `openai/` model prefix and legacy overrides.

The three-call smoke establishes provider compatibility only. Retained interpretation checks are unchanged; Luna changes the digest, so the pilot remains blocked on #63's supported recovery path. Attempt02 remains failed.

Executor validation: 67 targeted tests passed with `PYTHONPATH=src:scripts`; Ruff passed; mypy passed for the three LLM adapter files. An initial test invocation omitted PYTHONPATH and imported the separate foundation checkout, producing six option-test failures; corrected invocation tested this worktree. No database changes or pilot rerun occurred.
