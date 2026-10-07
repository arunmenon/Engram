# Priority buckets1–3 — independent review summary

Three separate Astra low-effort bulk reviews completed against unchanged working-tree source.22 existing issues covered; no runtime edits/cloud calls/alternative backend service runners. Local backend-neutral probes, including MemoryGraphStore, are not real-Spanner evidence. Findings refine existing issues; no issue closed and no compatibility sign-off.

| Bucket | Issues | Outcome |
|---|---|---|
|1 ingestion/data protection |4,5,14,15,16,17,19,28,33 | Five planned bugs confirmed;15/16 scoped-ready;28 single/batch scoped-ready with import proof outstanding;33 needs additional scan-progress/read-bound work |
|2 projection/evidence |8,9,10,18,20,29,30 | All seven planned fixes remain valid; replay overwrite and candidate-before-projection requirements added |
|3 retrieval |6,7,24,25,31,32 | All six planned fixes remain valid; rejected joins, uncertain negative claims, typed identity/session isolation and native termination proof refined |

Priority: protect accepted content with coordinated19/14; define4/5 and apply17 through the shared ingestion boundary. Fix26/27 prerequisite regressions where required for safe verification. Progress independent projection fixes20/8/9, then ordering/evidence10/29/18/30 with reliable retry and retention gates. Retrieval order:31 independently;7 before6;25 coordinated with29;24 after ordering/lineage contracts;32 deadline design now, acceptance only after native termination/cleanup proof. This is sequencing within the user-prioritized buckets, not a new platform redesign.

Additional obligations:33 must advance past retained oldest prefixes and bound actual reads, not only deleted IDs.29 must preserve derived fields after project→enrich→reproject.10 must defer before model candidate construction.18 requires both authoritative predecessor selection and eventual endpoint repair.7 must filter relationships before both traversal and completeness scope joins.6 may assert no_link/proposed_only only for completed relevant checks.25 needs typed Event/Entity identity and session-scoped evidence.32 must prove SDK stream/retry/thread termination, not merely response timeout.

Reports:2026-10-07-astra-bucket1-review.md,2026-10-07-astra-bucket2-review.md,2026-10-07-astra-bucket3-review.md. Request/source fingerprints:implementation-bucket-review-requests.json. Exact issue scopes/review evidence:implementation-waves.csv. No historical cloud scenario reclassification during review.
