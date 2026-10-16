---
schema_version: 1
artifact_id: N-20260926-16
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2102846005297225762", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:neonronin.sh/blog/jev-router-latency
claim_cluster: url:neonronin.sh/blog/jev-router-latency
feeds: ["decision"]
primary_source: https://neonronin.sh/blog/jev-router-latency/
source_commit: b752a26cc0ee73bc305b5535c11295839bb31d3d
strength: repo-pinned
pillar_primary: R7
pillar_secondary: ["R4"]
tags: {"mechanism": ["API gateway overhead", "batching questions per call"], "workload": ["decision-model calls via gateways"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: 3,000 timed requests per route and batch size", "control": "medium: same client, alternating routes, 100 runs per workload per route, one machine and network", "independence": "high: independent builder", "reproducibility": "high: benchmark code at a pinned commit", "applicability": "medium: sets the latency floor for any per-turn decision call we add (recall gate, rerank)"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A hosted decision-model call costs about 200 ms median direct; gateways add 31 to 48 ms (OpenRouter) or fail most requests under rate limits (Vercel, 389 of 1,000 succeeded in this test)"]}
claim_correction: none
---

# Jev router latency: direct vs OpenRouter vs Vercel AI Gateway (neonronin.sh)

- **URL:** https://neonronin.sh/blog/jev-router-latency/ ; code https://github.com/pandemicsyn/fafo/tree/main/benchmarks/jev-latency
- **Type:** builder writeup + repo
- **Author / org:** @pandemicsyn (neonronin.sh)
- **Date:** 2026-09-22
- **Retrieved:** 2026-09-26; repo pandemicsyn/fafo HEAD `b752a26cc0ee73bc305b5535c11295839bb31d3d` (2026-09-23) via GitHub API; not cloned
- **Cited by evidence:** https://x.com/pandemicsyn/status/2102846005297225762 (@pandemicsyn)
- **Relevance to a memory stack:** medium. If we put a decision call on every turn (recall gate, rerank), the transport path sets the floor; this measures it.

## TL;DR
- 3,000 requests from a Mac; routes: TypeSafe direct, OpenRouter, Vercel AI Gateway; noul, choice and score questions in batches of 1, 4 and 16, plus a mixed 16; 100 runs per workload per route across two sessions, one request at a time.
- TypeSafe direct median **207 ms** (100/100 completed). OpenRouter adds **31 to 48 ms** median (100/100). Vercel AI Gateway median 297 ms but only **389 of 1,000** requests succeeded (593 rate-limited, 18 server errors).
- Author: fine for background evals; for sub-100 ms interactive decisions, measure direct vs routed yourself.

## What it claims / describes
- End-to-end latency for complete responses by route and batch size; the post recommends OpenRouter over Vercel for reliability despite overhead.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| direct median latency | 207 ms | | TypeSafe API, 100/100 | one location |
| OpenRouter overhead | +31 to 48 ms median | direct | 100/100 | |
| Vercel median | 297 ms | | 35/100 completed in the cited workload | |
| Vercel completion | 389 / 1,000 | | 593 rate-limited, 18 server errors | free-tier period (inference; not stated) |

## Mechanism details you could implement
- Batch questions that share a state into one call (the benchmark varies 1 / 4 / 16 per call); pick the transport by measured p50 and error rate, and keep a fallback when the gateway rate-limits.

## Limitations, caveats, counter-evidence
- One machine and network location; sequential requests only (no concurrency); batch-size effects not captured in the fetched summary.
- Vercel results may reflect the free promotional period rate limits (inference).

## Takeaways for tuning a memory stack
- Budget about 200 to 250 ms per hosted decision call on the read path; a per-turn recall gate plus rerank is about 0.5 s before retrieval.

## Open questions
- p95 and behaviour under concurrency? Not captured.

## Grading and labels
- Directness high; control medium; independence high; reproducibility high (commit b752a26c); applicability medium.
- Pillar R7 (interfaces and gateways between agents and decision services). Secondary R4.
- Beliefs: no belief in the register covers transport latency; would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
post 2102846005297225762 (@pandemicsyn) -> neonronin.sh post (2026-09-22) -> results section -> repo pandemicsyn/fafo @ b752a26c. Independence: independent builder; related to OpenRouter's jev-router launch cluster (x:2103610898690855161) only by topic.
