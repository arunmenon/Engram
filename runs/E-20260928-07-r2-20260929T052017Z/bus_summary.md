---
schema_version: 1
artifact_id: RUN-E-20260928-07-r2-20260929T053725Z
artifact_type: run_result
producer: executor
run_id: E-20260928-07-r2-20260929T052017Z
created_at: 2026-09-29T05:37:25Z
input_refs:
  - {artifact_id: E-20260928-07-r2, file_id: 1FLC1Q3loKcLpiZyuG2_dqtCsrgf1Og-W, sha256: ec5507618cea940d24263412d0ef7072b355ba146c954f6c0491d5ca3af64c35}
supersedes: null
idempotency_key: run:E-20260928-07-r2:20260929T053725Z
status: complete
---
# E-20260928-07-r2: does a stray opinion among retrieved memories sway Jev?

We gave Jev 200 real decisions from Engram's own repository history: 100 "does this newer document replace that older one?" and 100 "is this statement still true?". We asked each one five ways. Without any related memories. With the five most related memories pasted in as plain text. And with the same memories in a structured field, once plain and once with each sentence's source marked and opinions flagged "unverified". Then we planted a single wrong opinion among the related memories 400 times. That was 2,260 calls, about 10 US cents. Adding related memories does not make Jev worse on its own: it got 13% wrong without them and 14% with them, and confident wrong answers stayed at 4%. But a single planted opinion pulled Jev to the wrong answer about a third of the time (32%). Marking sources and flagging opinions cut that to 23%. By the spec's rule the result is negative: plain-text related memories are acceptable for automatic writes. The practical point for Engram is that anything retrieved into a Jev decision is a lever on that decision. Recommended next step: when retrieved memories are passed to Jev, send them in the structured, source-marked form, which costs nothing and removes over a quarter of the planted-opinion effect (9 of 32 points). Separately, test whether dropping unverified opinion sentences altogether does better than flagging them.

## Numbers (Jev jev-1.13.0; 200 items in 177 decision threads; bounds are 95% cluster-bootstrap intervals over threads, 10,000 resamples)

Delivery: every neighbour arm passed all three checks (canary nonce quoted 20/20 in B, C1 and C2; neighbour bytes present in 100% of bodies; billed-token difference to the paired no-neighbour call at least 0.9 x the frozen neighbour token count in 100% of calls).

| Arm | What Jev saw | Error | High-confidence wrong (conf >= 0.8) | Precision at conf >= 0.8 | Corrections / damage vs A |
|---|---|---|---|---|---|
| A | targets only | 0.130 | 0.040 | 0.937 | |
| A' | A again (floor) | 0.130 | 0.045 | 0.929 | 1 / 1 |
| B | + 5 neighbours as free text | 0.140 | 0.040 | 0.941 | 6 / 8 |
| C1 | + neighbours in a typed field | 0.140 | 0.045 | 0.935 | 6 / 8 |
| C2 | + typed field, source class, opinion sentences marked unverified | 0.120 | 0.035 | 0.947 | 9 / 7 |

Planted-opinion capture (share of probe decisions equal to the planted wrong answer, 200 per cell):

| Arm | opinion at rank 1 | opinion at rank 5 |
|---|---|---|
| B | 0.325 | 0.320 |
| C1 | 0.285 | 0.255 |
| C2 | 0.240 | 0.225 |

Decisive paired tests:
- HCW(B) minus HCW(A): 0.000 [-0.020, +0.020]; err(B) minus err(A): +0.010 [-0.026, +0.048]. Both upper bounds below the 0.05 margin, so **d1_pass = true**.
- Capture B minus C2: +0.090 [+0.059, +0.123] (power 0.84); guardrails err(C2) minus err(B) -0.020, HCW(C2) minus HCW(B) -0.005, HCW(C2) minus HCW(A) -0.005, all below 0.05, so **d2_pass = true**.
- Flip rate against A: B 0.07, C1 0.07, C2 0.08, against a floor of 0.01 (excess about 6 to 7 points).

**Spec rule (`verdict.json`): negative** (d1 is checked first: free-text neighbours do not raise errors or confident errors beyond the margin, so B is allowed for automatic writes). d2 also passes, so C2 is a real mitigation of opinion capture, reported beside the outcome.

## Weaker than the spec wanted

- **Model labels.** Gold answers are Claude labels reviewed by Codex (at most 3 rounds), per policy v2; answer kappa 0.91 first pass, 0.96 final; 4 items contested. Planted opinions were written and checked by the same loop.
- **Neighbours are BM25, not the serving path.** The top-5 neighbours were retrieved once by BM25 over 5,118 document and commit chunks, standing in for /v1/context, which was not running where the dataset was built.
- **No H10 seeded history.** All 200 items come from the Engram repository's own history (117 versions of 75 docs); the spec's H10 seeded decisions were not needed to reach 200.
- **Source class from event type.** P5 has not landed, so C2's source class comes from the originating event type (recorded as `event-type` in the manifest).
- **Harness fixes before the run.** The delivery check used to compare raw neighbour text with a JSON body and passed 0 of 2,260 calls in the labelling session's replay. It now compares JSON-escaped fragments: 2,260 of 2,260 in a render-only replay before any call, with a unit test showing it still fails when a neighbour is dropped. `nbr_tokens` from the frozen dataset is now carried into every call row, so the token check uses the pinned tokenizer count rather than a bytes/4 estimate. Failed calls are retried (1 of 2,260 needed it). None of this touches the scorer's rule.
- **Policy gates.** The spec's challenger-review and accepted-decision gate were replaced by the CTO's fast-track queue and policy v2.

## Files

`calls.jsonl`, `delivery.csv`, `gold_metrics.csv`, `probe_capture.csv`, `paired_tests.csv`, `diagnostics.csv`, `verdict.json`, `run_manifest.json`, `receipts.sha256`. Commands from `harness/`: `python -m linkstale.run --manifest <cfg>`, `python -m linkstale.score --run <this dir> --dataset <LINK-STALE-200>`.


## Run manifest

```json
{
 "budget": {
  "calls": 2260,
  "caps": {
   "calls": 2400,
   "cost_usd": 2000.0,
   "tokens": 500000000,
   "wall_clock_s": 86400.0
  },
  "cost_usd": 0.0,
  "tokens": 2510095
 },
 "bundle": {
  "billed_input_tokens": 2439975,
  "billed_output_tokens": 70120,
  "calls": 2260,
  "dataset": "LINK-STALE-200",
  "dataset_manifest_sha256": "024970d298ee9e29a9f5152c55395dff888f7cc45542013ba550992fea9f827b",
  "ended_at": "2026-09-29T05:36:11Z",
  "finalised_at": "2026-09-29T05:37:25Z",
  "harness_commit": "4e1bb1f49dc1a2191420ecf5aa8f1cded2455600",
  "labels": "model labels (Claude labels, Codex review, max 3 rounds), used as gold per policy v2",
  "model_pins": {
   "jev": "jev-1.13.0 (requested and reported)"
  },
  "pre_run_fixes": [
   "bytes_present compares JSON-escaped neighbour fragments (was raw newline-joined text; 0 of 2,260 passed in the render-only replay, now 2,260 of 2,260)",
   "nbr_tokens carried from the frozen dataset into every item and probe row (scorer no longer uses the bytes/4 fallback)",
   "failed calls retried up to 3 times (1 call needed a retry)"
  ],
  "run_id": "E-20260928-07-r2-20260929T052017Z",
  "source_class_provenance": "event-type",
  "spec_file_id": "1FLC1Q3loKcLpiZyuG2_dqtCsrgf1Og-W",
  "spec_id": "E-20260928-07-r2",
  "spec_sha256": "ec5507618cea940d24263412d0ef7072b355ba146c954f6c0491d5ca3af64c35",
  "started_at": "2026-09-29T05:20:22Z",
  "status": "complete",
  "usd_basis": "input tokens x 0.042 USD per million (Jev list rate used by genigrep da10c5e)",
  "usd_estimate": 0.1025
 },
 "call_count": 2260,
 "command": "/Users/arunmenon/MemoryRSI-Signals/work/executor-engram/harness/linkstale/run.py --manifest /private/tmp/claude-501/-Users-arunmenon-MemoryRSI-Signals-work-executor-engram/3c31a4a6-fd80-4420-a1cf-c11684dd8f2c/scratchpad/cfg07.json",
 "dataset": "LINK-STALE-200",
 "dataset_manifest_sha256": "024970d298ee9e29a9f5152c55395dff888f7cc45542013ba550992fea9f827b",
 "decoding": {
  "note": "TypeSafe exposes no decoding parameters on /v1/systemone; served model version recorded instead"
 },
 "ended_at": "2026-09-29T05:36:11Z",
 "git_clean": true,
 "harness_commit": "4e1bb1f49dc1a2191420ecf5aa8f1cded2455600",
 "jev_model": "jev-1.13.0",
 "jev_model_version_pinned": "jev-1.13.0",
 "opinion_rule_sha256": "be9f593a9612c9eeef064318f57fa7f027533d7692ae5da0ca3cace8ae62aee8",
 "policy_snapshot": {
  "budget_per_run": {
   "cost_usd": 2000.0,
   "tokens": 500000000,
   "wall_clock_h": 24.0
  },
  "budget_per_week": {
   "cost_usd": 10000.0,
   "runs": 1000
  },
  "concurrency": 1,
  "dogfood_tenants_named": [],
  "permitted_datasets": "[public benchmarks, seeded fixtures, the Engram repository's own history]",
  "policy_sha256": "b22dfab07df9e60f4952ddd3bd2f9467dff1f3fcf65fa6306f51945ec42ec191",
  "policy_version": "2.0",
  "status": "set"
 },
 "render_only": false,
 "request_schema_version": "systemone v1 {state, model, questions}",
 "rows_rendered": 2260,
 "source_class_provenance": "event-type",
 "spec": "E-20260928-07-r2",
 "started_at": "2026-09-29T05:20:22Z",
 "stop_reason": null,
 "template_sha256": "d67d3cbbe63846938f6267bb4a015fc5790fd2ebcdd3d3b43be6ffbe5787fe2a"
}
```
