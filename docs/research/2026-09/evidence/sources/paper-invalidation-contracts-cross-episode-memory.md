---
schema_version: 1
artifact_id: N-SURVEY-20260930-07
artifact_type: note
producer: triage
run_id: survey-20260930T054503Z-298f
created_at: 2026-09-30T05:59:00Z
idempotency_key: note:survey:arxiv:2609.00243
input_refs: []
pillar_primary: R7
pillar_secondary: [R2, R1]
memory_stage: staleness
beliefs_affected:
  supports: [B22]
  contradicts: []
evidence: {directness: medium, control: high, independence: medium, reproducibility: high, applicability: medium}
strength: paper-ablated
source_url: https://arxiv.org/abs/2609.00243
found_via: survey
---

# Invalidation Contracts for Cross-Episode Agent Memory

- **URL:** https://arxiv.org/abs/2609.00243 (HTML v1 read: https://arxiv.org/html/2609.00243v1); server https://github.com/arquicanedo/self-reflective-apis ; client harness https://github.com/beining1008/cross-episode-memory-client (neither cloned)
- **Type:** paper
- **Author / org:** Michael Wu (South Dakota State University), Arquimedes Canedo (Siemens Digital Industries Software)
- **Date:** 2026-08-31
- **Retrieved:** 2026-09-30 (local copy: out/log/raw/2609.00243.html)
- **Cited by evidence:** survey run survey-20260930T054503Z-298f, R7 question 3 (a testable contract between a source and an agent's memory)
- **Relevance to a memory stack:** medium to high. It is an explicit wire contract that tells a memory which cached items a source change has made stale, with an ablation over invalidation granularity across seven models.

## TL;DR
- An agent caches "recovery suggestions" (fixes learned from API errors) across episodes. When server data drifts, cached fixes fail silently. The contract makes the server attach version stamps and cacheability hints to every suggestion so the client can evict exactly the stale entries.
- Row-level invalidation has eviction precision 1.00 on every model. Table-level invalidation has precision 0.25 on five of seven models (0.31 and 1.00 on the other two) and "drops post-drift first-try rates to 0% on five of seven" for entries that shared the table and were still valid.
- Row-level invalidation raises first-try compliance by 0 to 66.7 points over memory with no invalidation and recovers 29 to 33 % of baseline token cost on four of seven models. The contract "adds 15% to response payload".
- The same bytes are used very differently by different planners: "100% first-try compliance on Claude Haiku 4.5 and 11% or below on Claude Sonnet 5", which refuses fixes that add fields the original request lacked ("input-schema conservatism").
- Validity (is the cached item still right) is deterministic and vendor-independent; compliance (does the model apply it) is model-dependent. The paper separates the two.

## What it claims / describes
Contract fields (as extracted):
- Per suggestion: `cache_hint` ("cacheable" or "recompute"); `table` (the reference table the suggestion depends on); `tables` (a dependency vector `[{table, version}, ...]` for multi-table dependencies, level 4 and above).
- Per response: `table_versions` (map of table name to version string); `rules_version` (12-character SHA-256 prefix of the derivation-rule declarations, level 6).
- The server declares the contract on every response, success or error, inside a `recovery_feedback` envelope.

Client checking policies:
- Lazy (failure-gated): check `table_versions` only when a cached suggestion fails on first try.
- Stamp-only: check on every response.
- Stamp plus vectors: check on every response and compare cached dependency vectors.
- Oracle: uses the rule declarations.

On a version mismatch:
- Table-level (arm A2): evict every cached entry from that table.
- Row-level (arm A2D): the server returns a structured diff; the client evicts only changed rows and restamps the rest.

Arms: A0 no memory (cost baseline); A1 memory without invalidation; A2 table-level; A2D row-level with diffs; A2DC plus consumer notification; A2DG plus subgraph propagation; A2DO plus rule-declaration oracle.

Setup: two synthetic API domains. Acme Billing: 36-episode stream, 4 constraint classes; a promotional code table rotates after episode 11 (breaking) and a payment-token table bumps after episode 23 (benign). Recipe Conversion: 48-episode stream. Seven models over three serving paths: claude-haiku-4-5, claude-sonnet-4-6, claude-sonnet-5 (direct); gpt-5.4-mini, deepseek-v4-flash (gateway); gpt-5-mini, gemini-3.5-flash (translation layer). Three seeds per cell, about 9,400 episodes over 250 arm-level runs. Metrics are computed from request outcomes and billed tokens; no LLM judge.

## Numbers
First-try compliance on the drifted stream (percent):

| Model | A1 | A2 | A2D | A2D minus A1 | Eviction precision A2 | Post-drift first-try, "funding" class (not targeted by the drift): A1 / A2 / A2D |
|---|---|---|---|---|---|---|
| claude-haiku-4-5 | 44.4 | 100.0 | 100.0 | +55.6 | 0.25 | 66.7 / 0.0 / 66.7 |
| claude-sonnet-4-6 | 25.9 | 81.5 | 88.9 | +63.0 | 0.25 | 66.7 / 0.0 / 66.7 |
| claude-sonnet-5 | 0.0 | 3.7 | 11.1 | +11.1 | 0.25 | 66.7 / 0.0 / 66.7 |
| gpt-5.4-mini | 100.0 | 100.0 | 100.0 | 0.0 | 0.25 | 66.7 / 22.2 / 66.7 |
| deepseek-v4-flash | 3.7 | 7.4 | 3.7 | 0.0 | 0.31 | 66.7 / 66.7 / 55.6 |
| gpt-5-mini | 33.3 | 100.0 | 100.0 | +66.7 | 0.25 | 66.7 / 0.0 / 66.7 |
| gemini-3.5-flash | 29.6 | 63.0 | 77.8 | +48.2 | 1.00 | 0.0 / 0.0 / 11.1 |

A2D eviction precision is 1.00 on all models.

Token saving against each model's own A0 (percent), net of the contract's 15.1 % wire overhead, and retries per stream:

| Model | Saving A1 | Saving A2D | Retries A0 / A1 / A2D |
|---|---|---|---|
| claude-haiku-4-5 | 22.3 | 32.5 | 27.0 / 13.0 / 7.0 |
| claude-sonnet-4-6 | 18.6 | 29.2 | 27.0 / 14.7 / 8.3 |
| claude-sonnet-5 | 5.3 | 8.7 | 32.3 / 27.7 / 25.3 |
| gpt-5.4-mini | 28.2 | 31.0 | 24.0 / 7.0 / 7.0 |
| deepseek-v4-flash | 7.1 | 6.0 | 20.0 / 16.0 / 16.7 |
| gpt-5-mini | 16.4 | 32.1 | 27.0 / 14.0 / 7.0 |
| gemini-3.5-flash | 10.3 | 22.5 | 82.7 / 68.3 / 55.0 |

Detection policies on the rule stream (36 episodes; identical counts for the three Claude models):

| Policy | First-try | Retries | Evictions | Token change against lazy |
|---|---|---|---|---|
| Lazy | 28 | 8 | 2 | reference |
| Stamp-only | 22 | 14 | 4+5 | +14.0 to +14.3 % |
| Stamp plus vectors | 28 | 8 | 2 | −0.11 to +0.20 % |
| Oracle | 27 | 9 | 3 | +2.42 to +2.45 % |

Other: seed standard deviation at most 18.1 points; "zero contract failures in the entire evaluation"; latency not stated. A pre-registered prediction failed: the gain of naive memory was predicted to grow with drift frequency and instead plateaued at three rotations.

Text versus table: the abstract says row-level invalidation gains "55.6 to 66.7 on three" models; the table shows haiku-4-5 +55.6, sonnet-4-6 +63.0, gpt-5-mini +66.7. Consistent.

## Mechanism details you could implement
- Every memory item derived from a source carries the source's identity and version at derivation time (a dependency vector), plus a hint on whether it may be reused.
- The source publishes its current versions on every read. On mismatch, ask for a diff and invalidate only items whose dependency rows changed; restamp the others with the new version.
- Do not invalidate at the coarse unit (whole table, whole file, whole repository): it evicted three valid entries for each stale one here and removed the benefit for the unaffected class.
- Checking stamps on every response without dependency vectors over-evicts (14 retries against 8). Use stamps plus vectors, or check lazily on failure.
- Measure two things separately when a memory item is served: whether it was valid, and whether the model applied it on the first attempt. A valid memory that the model ignores is a compliance problem, not a staleness problem.

## Limitations, caveats, counter-evidence
- Stated: both API domains are synthetic and authored for the study; transfer to production APIs with organic drift is unknown.
- Stated: two domains; one base prompt per domain; one task family per class; prompt sensitivity untested.
- Stated: multi-table dependencies are implemented server-side but the subgraph arm bundles graph propagation with row diffs.
- (inference) The cached items are API error fixes, not engineering knowledge. The mapping to our case is structural: memory derived from a file, ticket or requirement, invalidated when that artifact changes.
- (inference) The contract assumes the source can emit versions and diffs. Git-backed sources can; many ticket and document tools expose only a last-modified time, which corresponds to the table-level arm.
- The compliance spread (0 % to 100 % on identical bytes) means results from one planner model do not transfer to another.

## Takeaways for tuning a memory stack
- H10's staleness arm says to test "source-change invalidation" first. This paper says the granularity of that invalidation decides whether it helps: item-level precision 1.00 against 0.25 for the coarse unit. P5's provenance fields should record the dependency at the finest unit the source can version (file plus blob hash or line range, ticket field, requirement clause), not only the source id.
- The contract is a candidate clause for the one-scoped-interface contract in B22: a store adapter declares whether it can return versions and diffs, and the snapshot level it can therefore honour.
- When a memory is served and the agent does not use it, log that separately. Model upgrades can change compliance sharply (claude-sonnet-4-6 88.9 against claude-sonnet-5 11.1 under the same arm).

## Open questions
- What is the eviction precision of file-level against hunk-level invalidation on a real repository history?
- Does a decision-model staleness audit (H10a) add anything once item-level source-change invalidation is in place?
- How should invalidation propagate through derived nodes (a summary of several items, a link between a requirement and a pull request)?
