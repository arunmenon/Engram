# Astra G05 scoped source review

Reviewer: existing Astra medium agent astra_g04_review. Read-only review, no cloud execution.

Initial review reproduced unrelated word-seed expansion in CQ1/CQ4 and recommended neutral query texts. We retained the original questions and instead fixed the underlying fallback behavior, tracked in #50.

Recheck verdict: no concrete blockers. Resolved explicit seeds now suppress loose-word fallback; independent key/number/pattern references and unanchored discovery remain. Both G05 local tests passed, including the eight unchanged questions. Success-only retention requires complete journey plus clean shutdown; first-only, failure and shutdown errors do not retain. Ownership checks and cleanup preserved. Approved for scoped G05 cloud run.

Local validation: 52 focused tests passed; broader suite 66 passed, one failure. The failure in test_pdlc_retrieval_eval.py::TestReviewFindings::test_no_keyword_uses_artifact_edges_only also reproduces on unchanged HEAD: owner query returns Component plus Deployment. Recorded separately; not caused by #50 and not silently fixed or counted passing. Monitoring export permission remains unavailable.
