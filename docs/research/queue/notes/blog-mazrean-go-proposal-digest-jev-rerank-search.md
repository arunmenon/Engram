---
schema_version: 1
artifact_id: N-20260928-36
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:52:00Z
input_refs: [{"artifact_id": "post:2104512165524951441", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:zenn.dev/mazrean/articles/bd9b563ace18db
claim_cluster: url:zenn.dev/mazrean/articles/bd9b563ace18db
feeds: ["decision"]
primary_source: https://zenn.dev/mazrean/articles/bd9b563ace18db
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R3"]
memory_stage: reranking
priority: 1
tags: {"mechanism": ["vector search then Jev noul relevance filter", "absolute score threshold 0.2", "sort by Jev probability"], "workload": ["small site search", "Go proposal digests"], "lifecycle_stage": ["retrieval", "reranking"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: a real deployed search, but only cost and latency are reported, not result quality", "control": "low: no baseline measurement, only a qualitative comparison with Google site search", "independence": "high: an independent builder with no stake in TypeSafe stated", "reproducibility": "low: no code, no question text, corpus size not stated", "applicability": "low: a small public site search, not engineering-agent memory"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": []}
claim_correction: The quoting post says "Jev scores relevance 0-1 -> sort"; the article uses one Jev noul (yes/no) per candidate, keeps those at 0.2 or above, then sorts, and reports no quality measurement at all.
---

# Jev as a reranker for a small site search: Go Proposal Weekly Digest (mazrean, Zenn)

- **URL:** https://zenn.dev/mazrean/articles/bd9b563ace18db (Japanese)
- **Type:** builder writeup
- **Author / org:** mazrean (individual builder); site go-proposal-weekly-digest.mazrean.com
- **Date:** 2026-09-26
- **Retrieved:** 2026-09-28 (web page, no repository or code linked in the article as read)
- **Cited by evidence:** https://x.com/lambdascript/status/2104512165524951441 (@lambdascript, quoting @mazrean22 post 2103809325085147380)
- **Relevance to a memory stack:** low to medium. A first-hand deployment of Jev (TypeSafe) at the reranking stage with an absolute threshold, which is the pattern the synthesis warns about, but with no quality numbers.

## TL;DR
- Pipeline: bge-m3 embeddings (hosted on Cloudflare Workers AI), vector search narrows to 20 candidates, one Jev noul per candidate asks whether it is relevant, candidates at 0.2 or above are kept and sorted by that value.
- Cost: "検索1回あたり約 $0.0002" (about $0.0002 per search); about $0.016 per month at the site's traffic (about 200 page views a week).
- Latency: quoted vendor range "70～500 ミリ秒で回答"; observed "間隔を開けずにリクエストを行うと数百 ms 程度で応答が返り、間隔があくと1秒以上" (a few hundred ms when requests come back to back, over 1 s after a gap). No percentiles, no n.
- **Claim correction:** the quoting post describes a 0-1 relevance score followed by a sort; the article uses noul probabilities with a fixed 0.2 cut, and measures no search quality. The only comparison is a qualitative "better than Google site search".

## What it claims / describes
A search box for a weekly digest of Go language proposals. Step 1: embed the query with bge-m3 and retrieve the top 20 digest entries by vector similarity ("事前にベクトル検索で 20 個に候補を絞り込んだうえで、Jev でリランクする"). Step 2: ask Jev one noul question per candidate on relevance ("Noul の質問として投げることで関連度を判定、値が 0.2 以上で返ったもの"). Step 3: drop candidates below 0.2 and order the rest by the probability. The exact question text, the model version and the API call are not stated in the article as read.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| cost per search | about $0.0002 ("約 $0.0002") | none | 20 candidates, one noul each | Jev price assumption not restated; corpus size not stated |
| monthly cost | about $0.016 ("毎月 $0.016 程度") | none | about 200 page views a week | an estimate, not a bill |
| latency, back-to-back requests | "数百 ms 程度" (a few hundred ms) | none | not stated | no percentiles, no n |
| latency, after an idle gap | "1秒以上" (over 1 s) | none | not stated | suggests a cold path (inference) |
| search quality | not measured | Google site search, qualitative only | none | no labelled queries |

## Mechanism details you could implement
- Two-stage read: dense retrieval to a fixed pool of 20, then a per-candidate yes/no relevance question, then threshold 0.2 and sort by probability.
- The 0.2 cut is an absolute floor on a pointwise noul, set by hand. The synthesis (section 2) records that a "nothing relevant" floor can empty result sets and lose gold evidence (B11); a 0.2 floor on a public search box can return an empty page, and the article does not say what happens then.

## Limitations, caveats, counter-evidence
- No quality measurement, no labelled queries, no comparison with the vector ranking alone.
- Pointwise nouls, not one listwise choice: B10 (Hindsight) reports a single listwise choice beating per-item yes/no on recall@1 with 30x fewer calls; this deployment uses the pattern that lost there.
- Cold-start latency above 1 s after idle periods matters for interactive reads (inference: connection or capacity warm-up; cause not stated).
- No instruction-bearing content found.

## Takeaways for tuning a memory stack
- Nothing here changes a design choice; it is a usage datapoint: Jev at the reranking stage is cheap enough (about $0.0002 for 20 candidates) that cost is not the constraint.
- If we copy the pattern, keep ranking on and a minimum of one result (B11), and prefer a listwise call (B10).
- Measure warm versus idle latency separately; this builder saw a several-fold gap.

## Open questions
- What fraction of searches returned nothing at the 0.2 floor?
- Does the Jev reorder beat the bge-m3 order on any labelled set?

## Grading and labels
- Directness medium (a real deployment, but only cost and latency); control low (no baseline measured); independence high (independent builder); reproducibility low (no code or question text); applicability low (small public site search).
- Pillar R9 primary (a System One model at a stage), R3 secondary. Stage: reranking. Priority 1. Strength: builder-report.
- Beliefs: none supported or contradicted with measurements. Context only: the pattern departs from B10 (listwise beats pointwise) and B11 (no absolute floor on a ranker) without testing either.

## Origin chain
@lambdascript post 2104512165524951441 quotes @mazrean22 post 2103809325085147380, which links the Zenn article; the article is the primary source (sections on architecture, cost and latency). Independence: single author, no shared authors, datasets or harnesses with other Jev reranker sources (Hindsight, hev/reranker, rerank-bench).
