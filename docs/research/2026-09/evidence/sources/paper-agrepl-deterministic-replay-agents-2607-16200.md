---
schema_version: 1
artifact_id: N-SURVEY-20260927-14
artifact_type: note
producer: triage
run_id: survey-20260927T054501Z-e1b9
created_at: 2026-09-27T05:53:00Z
idempotency_key: note:survey:arxiv:2607.16200
input_refs: []
pillar_primary: R1
pillar_secondary: []
beliefs_affected: {supports: [B1], contradicts: []}
evidence: {directness: 3, control: 1, independence: 3, reproducibility: 3, applicability: 3}
source_url: https://arxiv.org/abs/2607.16200
found_via: survey
strength: builder-report
---

# Deterministic Replay for AI Agent Systems (agrepl)

- **URL:** https://arxiv.org/abs/2607.16200 (read via https://arxiv.org/pdf/2607.16200; the HTML v1 URL returned 404); repo README https://raw.githubusercontent.com/taiwrash/agrepl/main/README.md
- **Type:** paper (with open-source tool)
- **Author / org:** Rasheed Mudasiru, Federal University of Technology Minna (single author)
- **Date:** arXiv 2607.16200 (July 2026 id); PDF metadata creation date 30 Apr 2026
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, pillar R1, belief B1
- **Relevance to a memory stack:** medium, it is a concrete design for retaining everything served over the wire and replaying it by key lookup, but its "determinism" is replay of recorded outputs, not re-execution of the model.

## TL;DR
- agrepl is a Go CLI that runs the agent behind a MITM HTTP(S) proxy, records every request/response pair (including LLM API calls) to a JSON trace, and on replay injects stored responses with all outbound TCP refused.
- Its core insight, verbatim: "determinism during replay is achievable not by controlling the model or API, but by replacing them with their previously recorded outputs."
- Fidelity F = 1.0 is tautological by construction: the paper says F = 1.0 "is unconditionally achievable under the replay model because no external system is invoked"; F below 1.0 only signals a matching failure or a replay-engine bug.
- Evaluation: five small workloads, reported "250 replay instances" but the setup text says each workload "was recorded once and replayed five times" (5 x 5 = 25); median latency reduction stated 98.3% while every per-workload row is 99.4 to 99.8%. No baselines.
- Code exists: MIT, github.com/taiwrash/agrepl, evaluated as v0.1.0-alpha; README confirms "Replay is a canonical key lookup, not a re-execution."

## What it claims / describes
Execution model. An execution E = (s1..sn); each step s_i = (tau_i, iota_i, o_i, mu_i) with type tau in {LLM, HTTP, TOOL, SYSTEM}, input iota (prompt, request, or command), output o (completion, response, or result), metadata mu (timestamps, latency, token counts, protocol headers). Divergence set D(E,E') = { i : o_i != o'_i }. Four named nondeterminism sources: LLM sampling variance, external API state, CDN infrastructure headers, environment and timing noise.

Determinism invariant (verbatim structure): E' is a deterministic replay of E iff for all i in [1,n], o'_i = o_i, i.e. D(E,E') is empty. "This is unconditionally achievable under the replay model because no external system is invoked; all o_i values are returned directly from the stored trace T." Assumptions implicit rather than stated: the agent issues the same requests in the same order (so K matches), the agent process itself is deterministic given identical responses, and side effects outside the network are not needed (the limitations section admits filesystem and database writes are not captured).

Request key: K(s) = SHA256( method(s) | norm(url(s)) | H_body(s) ), where norm(url) removes transient query parameters and H_body(s) is the SHA-256 of the request body. Lookup L(s,T) = { o_j : K(s_j) = K(s), s_j in T }. If |L| > 1 (repeated identical requests) responses are returned in sequence order; if |L| = 0 in strict mode the proxy returns an explicit error (502) rather than going to the network. The README instead mentions "structural JSON matching for robust replays"; the paper says K(s) "requires exact match". These may be different versions (flag).

Fidelity: F(E,E') = 1 - |D(E,E')| / |E|. "Under the determinism invariant, F = 1.0 for all replay executions."

What is recorded. Record command forks the child with HTTP_PROXY/HTTPS_PROXY set; proxy built on goproxy; TLS via leaf certs signed by an ephemeral local CA installed into the child's trust store only. Trace is versioned JSON with run_id, command, timestamp, status, and steps each holding type, request (method, url, headers, body), response (status, headers, body), latency_ms; stored under .agrepl/runs/ and shareable to Cloudflare R2. LLM SDK calls (Gemini, OpenAI Go client) are captured as ordinary HTTPS bodies containing "prompts, generation configs, completions, and token usage". Strict mode (default) refuses all outbound TCP; --fallback forwards unmatched requests live. HTTP/1.1 and HTTPS only; gRPC and HTTP/2 on roadmap. Streaming not mentioned.

Noise-aware header diff. Built by analysing 100 pairs of runs to the same endpoint recorded 30 minutes apart. Tiers: Signal (always reported: Status, Location, Content-Type, X-Cache, Server); Noise (suppressed: Date, Age, X-Timer, X-Request-Id, X-Fastly-Request-Id, X-Served-By, Via); Removed (present in only one run, e.g. Set-Cookie/NID). Steps are matched between runs by K(s), not index. Diff is string level; LLM-assisted semantic diff of completions is "planned".

Five workloads: W1 single HTTP fetch; W2 three-step REST API chain; W3 LLM summarisation with one Gemini Flash tool call; W4 web search agent (4 HTTP steps); W5 code-generation agent with LLM call and file write. Ubuntu 24 AMD64, agrepl v0.1.0-alpha.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Replay instances | "250 total replay instances" | none | 5 workloads, "recorded once and replayed five times" | text arithmetic gives 25, not 250; unresolved disagreement |
| Fidelity | F = 1.0 on all workloads | none | strict mode | tautological: stored outputs are returned, model not re-run |
| W1 HTTP Fetch | live 48 ms, replay 0.3 ms, 99.4% | live run | Table II | per-step |
| W2 REST Chain | 185 ms, 0.9 ms, 99.5% | live | Table II | per-step |
| W3 LLM Summarise | 620 ms, 1.1 ms, 99.8% | live | Table II | LLM latency removed because LLM is not called |
| W4 Web Search Agent | 340 ms, 0.8 ms, 99.8% | live | Table II | |
| W5 Code Generation | 510 ms, 1.0 ms, 99.8% | live | Table II | file write not captured by proxy |
| Median reduction | "98.3%" (median row: 340 ms, 0.9 ms) | live | Table II | 340 to 0.9 is about 99.7%, and all rows are 99.4% or more; 98.3% is inconsistent with the table |
| Record overhead | median 1.8 ms per step (3.2% for W1, under 0.3% for W3) | live | | |
| Diff false positives | mean differences unfiltered 7.2 (all noise tier); filtered 0.0 | unfiltered | 100 same-endpoint pairs | same data used to build the taxonomy, so not held out |
| Diff detection | 12 of 12 injected semantic changes detected, precision = recall = 1.0 | none | 12 pairs | tiny n |
| Cost | not stated (README: no token consumption at replay) | | | |
| Setup time | "under 30 seconds" to first replay | | | claim, not measured in table |

## Mechanism details you could implement
- Transport-level capture of every served byte with a content-addressed request key (method, normalised URL, body hash) is directly reusable as an Engram "served artifact" key; it gives exact, non-substituting lookup, matching P0's "never silent substitution" rule.
- Strict mode (unmatched request is an explicit error, never a live fallback) is the right default for a review replay: it turns silent substitution into a visible failure.
- Sequence-ordered return for duplicate keys handles repeated identical calls.
- Signal/noise header tiers are a cheap way to avoid false-diff alarms when comparing a re-run against a record.
- Stack fingerprint is not recorded beyond what appears in HTTP bodies (model name in request); (inference) a memory stack would want to add model snapshot and provider metadata explicitly.

## Limitations, caveats, counter-evidence
- Not re-execution: replay returns recorded LLM outputs, so it says nothing about whether the model would produce the same output again. F = 1.0 measures replay-engine correctness, not model reproducibility.
- If the agent's own logic or request payloads vary (timestamps, UUIDs, nondeterministic prompt assembly), K(s) misses; paper admits "K(s) requires exact match" and fuzzy matching is future work.
- Filesystem and database side effects are not captured; W5 writes a file, so its replay covers only the network half.
- No baselines (VCR.py, Polly.js, WireMock are discussed but not measured), no variance reported, tiny workloads, single author evaluating own tool.
- Internal inconsistencies: 250 vs 25 instances; 98.3% median vs table rows all at or above 99.4%.
- Traces contain secrets and PII (Authorization headers, bodies); redaction is only "planned".
- No instructions aimed at an AI reader were found in the paper or README (README has marketing copy only).

## Takeaways for tuning a memory stack
- (inference) agrepl is the strong form of B1's "retain served artifacts": it retains every byte served, including the model's output. Under that form, a reviewer can re-inspect and even re-drive the agent's control flow exactly, but only because the model is replaced by its recording. This supports B1 for re-inspection and makes clear that the sufficiency claim needs the recorded output, not just the served context.
- For P0, the operational meaning of "reproduce" should be "replay by lookup with strict no-substitution"; agrepl shows this is cheap (about 1 ms per step) and implementable.
- B1's "whether necessary depends on whether sources retain versions natively" is consistent with agrepl: it records full HTTP responses precisely because remote sources (APIs, CDNs) do not retain versions and drift in 30 minutes.

## Open questions
- Does the published repo's matching (README: structural JSON) differ from the paper's exact SHA-256 K(s), and which version produced the reported numbers?
- How does replay behave when the agent under review is itself upgraded (different prompts, hence different keys)?
- Is streaming (SSE) LLM output captured faithfully?
- Where did the 250 figure come from?

## Grading
- directness 3: directly about replaying agent runs from retained served data, but only the lookup form, not re-execution or decision review.
- control 1: no baselines, fidelity is true by construction, no variance, internal numeric inconsistencies.
- independence 3: single author evaluating own tool, but no LLM judge and metrics are mechanical.
- reproducibility 3: MIT code public with a pinned alpha version; traces and workload scripts not stated as released.
- applicability 3: transport-level capture fits engineering agents on hosted APIs; misses filesystem and repo state that build-time agents change.
