---
schema_version: 1
artifact_id: N-20260929-28
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104819623824634287", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:unsloth.ai/docs/models/decision-laya
claim_cluster: url:unsloth.ai/docs/models/decision-laya
feeds: ["memory"]
primary_source: https://unsloth.ai/docs/models/decision-laya
source_commit: 6c20f0fac752a1ec64537575873fa7f835d348dd
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R7", "R8", "R4"]
memory_stage: none
priority: 2
tags: {"mechanism": ["system-one-decision-model", "open-weight", "jev-compatible-api", "noul-choice-score", "fp16-safetensors", "cpu-default-gpu-fallback", "context-window-reject-on-truncation"], "workload": ["classification", "routing", "support-tickets"], "lifecycle_stage": ["shipped-change", "self-hosting"], "cross_cutting": ["privacy-local-data", "threshold-transfer", "calibration-claimed-not-shown", "cost"]}
evidence_grade: {"directness": "high: vendor docs page plus the implementing code read at a pinned Unsloth commit", "control": "unknown: no comparison of any kind (no accuracy, no Jev parity run, no latency table)", "independence": "medium: Unsloth integrates weights published by convaiinnovations, so the integrator is not the model author (inference); still vendor documentation of its own feature", "reproducibility": "high for API shape and limits: route, validation limits and model catalog are in pinned AGPL code, Laya runtime vendored as laya 0.3.5 (Apache-2.0), weights on HF under apache-2.0", "applicability": "medium: keeps memory text in-house at near-zero marginal cost, but the 512 or 1024 token window rejects long PDLC artifacts with HTTP 422, so states must be chunked or summarised first"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": []}
claim_correction: Post implies existing Jev projects work by switching the base URL; the docs narrow this: confidence uses a different formula so Jev thresholds do not transfer, and choices past about 20 described options get their labels trimmed; code also refuses unknown request fields and over-window states
---

# Unsloth Decision API: serving Laya locally behind a TypeSafe/Jev-compatible endpoint

- **URL:** https://unsloth.ai/docs/models/decision-laya (implementation: https://github.com/unslothai/unsloth, `studio/backend/routes/systemone.py`, `studio/backend/core/systemone/catalog.py`, `studio/backend/core/systemone/laya_runtime.py`)
- **Type:** vendor docs page (GitBook) plus repo code
- **Author / org:** Unsloth AI (docs and Studio code, AGPL-3.0-only headers); Laya weights from Hugging Face repo `convaiinnovations/laya` (license tag `apache-2.0`, HF sha `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, lastModified 2026-09-24); vendored `laya` Python package 0.3.5, Apache-2.0 (`studio/backend/vendor/laya_manifest.json`)
- **Date:** docs page has no date; an embedded screenshot filename is dated "2026-09-28". Unsloth HEAD read: `6c20f0fac752a1ec64537575873fa7f835d348dd` (2026-09-29T04:31:46Z, "Library: equal size chat cards and no loading placeholders (#12221)"); the Laya files were read at that commit, their own introduction commit was not identified
- **Retrieved:** 2026-09-29. Docs via WebFetch and the page's Markdown export (`decision-laya.md`); code via raw.githubusercontent.com at the pinned sha (not cloned, per instructions); HF metadata via the HF models API
- **Cited by evidence:** X post 2104819623824634287 by @realfxw (Chinese); the post itself was not re-fetched, its content is taken from the triage brief
- **Relevance to a memory stack:** high for R9. First packaged, one-toggle path to run an open-weight System One model locally behind the same wire format and SDK as hosted Jev, which is exactly the "self-host and keep memory text in-house" arm of R9. Existing Laya notes (N-20260928-22 doomGemma, N-20260927-20 Privatemode benchmark, N-20260928-35 hermes-firewall, N-SURVEY-20260928-11 Laya model card, N-SURVEY-20260929-02 Laya recalibration, N-20260927-07 Raya) cover Laya quality; what is new here is the serving surface, its compatibility contract, its limits and its failure behaviour.

## TL;DR
- Unsloth Studio / Desktop now serves Laya on `POST http://localhost:8888/v1/systemone` with Jev's request shape (`model`, `state`, `questions` of type `noul` / `choice` / `score`) and Jev's response shape. The TypeSafe SDK works by setting `TYPESAFE_BASE_URL=http://localhost:8888`; the default model names `jev-latest`, `default`, `laya` (and in code also `jev-preview`, `openjev-latest`) map to whatever model is picked in Settings.
- Three checkpoints: Multilingual (default) 678 MB, "4GB RAM", 100+ languages, 1024-token context (mmBERT-base); English 846 MB, "5GB RAM", 512-token context (ModernBERT-large); Typed decisions 846 MB, "5GB RAM", English, fine-tuned on four typed-decision workflows, 1024-token context per code (the docs table gives no context for it).
- Format is fp16 `model.safetensors` pulled from HF, run in PyTorch (CPU default; CUDA / XPU / MPS, or MLX on Apple Silicon via `unsloth_zoo`), not GGUF. GPU out-of-memory falls back to CPU.
- Compatibility is partial, stated by the docs: `confidence` uses a different formula (normalised entropy, `1 - H(p)/log(k)` in vendored laya) so "a threshold tuned on Jev won't transfer; threshold on `probabilities` instead", and choice options share a fixed token budget so "past about 20 described options the labels get trimmed".
- No accuracy, calibration or latency numbers beyond "The first request loads the model, which takes 10 to 20 seconds. After that, requests take well under a second on most CPUs." The docs say "get back calibrated probabilities" without evidence (supports B14). Claim correction: the post's "just switch the base URL" is narrowed by the threshold and option-trimming caveats.

## What it claims / describes
**Setup (docs, Quickstart).** Install Unsloth Desktop (macOS, Windows, Linux) or the install script. "Go to Settings -> API -> **Decision API** and turn on **Serve requests**. The default Laya model (678 MB) will then start to download after confirming if you want to start the download." API key under "Access tokens" on the same page, or "turn on **Keyless API access** -> **Chat and inference** and skip the key on localhost." In code, the API is off by default (404 `api_usage_error`, "The Decision API is off. The Studio owner can turn it on in Settings > API."), and an environment kill switch beats the setting (test name `test_env_kill_switch_beats_the_setting`).

**Request (docs curl example, verbatim fields).**
```json
{"model": "laya",
 "state": "Hi, I was charged twice for my March invoice (#4411). Please refund the duplicate today.",
 "questions": {
   "team": {"type": "choice", "instructions": "Which team should handle this?",
            "criteria": {"billing": "invoices, payments, refunds", "technical": "bugs, outages, errors", "sales": "pricing, new plans", "other": "everything else"}},
   "refund": {"type": "noul", "instructions": "Does the customer ask for a refund?"},
   "urgency": {"type": "score", "instructions": "How urgent is this?", "criteria": ["not urgent", "soon", "today"]}}}
```
Header `Authorization: Bearer sk-unsloth-YOUR_KEY`.

**Response (docs, verbatim).**
```json
{"model": "laya-multilingual",
 "answers": {
   "team": {"type": "choice", "choice": "billing", "confidence": 1.0, "probabilities": {"billing": 1.0, "technical": 0.0, "sales": 0.0, "other": 0.0}},
   "refund": {"type": "noul", "noul": 0.9794},
   "urgency": {"type": "score", "score": 1.9005, "confidence": 0.698, "legend": {"0": "not urgent", "1": "soon", "2": "today"}, "probabilities": {"0": 0.004, "1": 0.0915, "2": 0.9045}}},
 "usage": {"input_tokens": 172, "output_tokens": 0}}
```
In code the `noul` answer also carries `"confidence": max(p, 1 - p)` (not shown in the docs example). Response header `x-typesafe-request-id` (uuid4) is set so the SDK finds a request id.

**Compatible API surface (what is and is not).**
| Item | Status | Locator |
|---|---|---|
| Endpoint `POST /v1/systemone` | compatible path | routes/systemone.py `@router.post("/systemone")`; docs curl |
| Base URL / SDK | `pip install typesafe-sdk`, `TYPESAFE_BASE_URL=http://localhost:8888`, `TYPESAFE_API_KEY=sk-unsloth-...` | docs "Migrating from Jev" |
| `model` aliases | `default`, `laya`, `jev-latest`, `jev-preview`, `openjev-latest` -> configured model; named: `laya-multilingual`, `laya-english`, `laya-typed-decisions`; local dir served as `laya-local` | catalog.py `DEFAULT_ALIASES`, `CHECKPOINTS` |
| `state` | "can be a string or any JSON"; max 200,000 characters | docs; `MAX_STATE_CHARS = 200_000` |
| `questions` | dict of `{type, instructions?, criteria?}`; extra keys per question forbidden | `QuestionIn` (`extra = "forbid"`) |
| Limits | "up to **64 questions**, with up to **255 options per choice** and **10 levels per score**"; question JSON max 20,000 chars | docs; `MAX_QUESTIONS`, `MAX_CHOICES`, `MAX_SCORE_LEVELS`, `MAX_QUESTION_CHARS` |
| `noul` criteria | may only have keys `"true"` and `"false"` | `_validate` |
| Unknown top-level fields | refused with 400 `api_usage_error` "Unsupported field(s)", comment: "an ignored OpenJev extension (`images`) answers a different question" | routes/systemone.py |
| `confidence` | different formula; do not reuse Jev thresholds | docs; vendored `laya/common.py` `confidence_from_probs`: "Normalized Shannon entropy confidence: 1 - H(p) / log(k)" |
| `score` value | expected value over levels, `sum(i * p_i)` | laya_runtime.py `_predict` |
| Choice option budget | "past about 20 described options the labels get trimmed"; code: `head_max_len` default 192 tokens for the question head | docs; `_predict` |
| Over-window state | rejected, 422 `invalid_request_error`: "State and questions exceed the Laya context window. Shorten the state or use fewer/shorter criteria." | routes/systemone.py; test `test_truncated_state_is_rejected` |
| Keyless callers | may use only the configured model (403 `permission_error` otherwise) | routes/systemone.py |
| Busy / loading | 503 `model_loading` with `Retry-After` (5 s); load wait 20 s, run wait 30 s, max 8 pending requests, 60 s backoff after a failed load | laya_runtime.py constants |
| Images, streaming, batch endpoints | not stated | none |

**Runtime (code).** One checkpoint resident at a time. Weights: `rl_agent_config.json`, `model.safetensors`, plus `encoder/` and `tokenizer/` folders downloaded from HF `convaiinnovations/laya` (subfolder `multilingual`, root, or `typed-decisions`). All three published checkpoints are stored fp16; on CUDA fp16 is used, on CPU fp16/bf16 only where the ISA supports it natively (AVX512-FP16 / AMX), otherwise fp32; if fp16 activations overflow, the batch reruns in fp32. Each question is scored as its own sequence with the state inserted after the question head, so the state is re-encoded once per question (inference from `_predict` building one item per head), and `usage.input_tokens` reflects that.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Multilingual weights | "678 MB" (catalog: 678_201_636 bytes) | none | docs table; catalog.py | download size |
| Multilingual minimum RAM | "4GB RAM" | none | docs table | not measured in the docs |
| Multilingual context | "1024 token context" | none | docs table | state plus question head share it |
| English weights / RAM / context | "846 MB" / "5GB RAM" / "512 token context" | none | docs table | post omits the 512 limit |
| Typed decisions weights / RAM | "846 MB" / "5GB RAM" | none | docs table | context 1024 per catalog.py description |
| Languages | "100+ languages" (Multilingual) | none | docs table | per-language quality not stated |
| First-request load | "10 to 20 seconds" | none | docs | hardware not stated |
| Steady-state latency | "well under a second on most CPUs" | none | docs | no percentile, no hardware, no n |
| Request limits | 64 questions, 255 options per choice, 10 levels per score | Jev limits not stated here | docs; code | |
| Example outputs | refund noul 0.9794; urgency score 1.9005, confidence 0.698; input_tokens 172 | none | one illustrative request | not an evaluation |
| Accuracy vs Jev | not stated | | | the HF card has `laya_vs_jev` images; covered by N-SURVEY-20260928-11, not read here |

## Mechanism details you could implement
- Arm swap by configuration only: keep the TypeSafe SDK, point `TYPESAFE_BASE_URL` at `http://localhost:8888`, send `model: "jev-latest"`; the server maps it to the configured Laya checkpoint. Name `laya-english` / `laya-multilingual` explicitly in arm tests so a Settings change cannot silently switch the model.
- Threshold on `probabilities[option]` (choice) and `noul` values, never on `confidence`; the docs example: "only file a bug report when `technical` is above `0.8`". Refit every gate threshold locally per model (see N-SURVEY-20260929-02 on recalibration).
- Keep choices at or below about 20 described options, or shorten descriptions; for id-selection prompts over many memory ids (jevmem style, up to 60 ids) this matters (inference).
- Treat HTTP 422 "exceed the Laya context window" as a routing signal: chunk the artifact or send a structured extract (title, section, decision fields) rather than the full PDLC document (inference).
- Handle 503 `model_loading` with `Retry-After`; pre-warm with one request at startup to absorb the 10 to 20 s load.
- Run `state` as JSON to keep typed artifact fields; the server serialises it with laya's `serialize_state`.

## Limitations, caveats, counter-evidence
- No accuracy, calibration, latency distribution or Jev parity numbers on the page; "calibrated probabilities" is asserted, not shown (B14).
- Context: 512 tokens (English) or 1024 (Multilingual, Typed decisions) including the question head. Long requirements, designs or PRs will be refused, not truncated; that is safer than silent truncation but means an extraction step before the gate (inference).
- Per-question re-encoding of the state means 64 questions cost about 64 forward passes over the same state (inference from code); throughput claims for large batteries are not stated.
- Licences differ by layer: Studio backend AGPL-3.0-only; laya package and weights Apache-2.0. Embedding Unsloth Studio in a product would carry AGPL obligations (inference; not legal advice).
- Only the three HF checkpoints or a local directory are served; the docs do not mention fine-tuned checkpoints, though code accepts a local folder via `UNSLOTH_SYSTEMONE_MODEL` / settings.
- The primary post (Chinese) was not re-fetched; its figures matched the docs except that it does not mention the English 512-token limit or the two compatibility caveats.
- Instruction-bearing content: the Markdown export of the docs page ends with a GitBook "Agent Instructions" section telling AI agents to query `GET https://unsloth.ai/docs/models/decision-laya.md?ask=<question>&goal=<endgoal>`. It was not followed; nothing in this note comes from it.

## Takeaways for tuning a memory stack
- This makes the R9 "open-weight, in-house" arm cheap to stand up: same client code, same question JSON, local data. The only code change for an A/B is the base URL plus refitted thresholds.
- Do not port Jev-fitted thresholds or any rule on `confidence`; refit on `probabilities`.
- Candidate stages for a local Laya arm on our workload: write_gate and linking on short units (a ticket title plus summary, a decision record, a PR description under 1024 tokens), recall_gate on the user request. Not suitable as-is for whole-artifact judgements.
- Keep option lists short; for supersession target selection over many ids, prefilter to at most about 20 candidates before the choice call.

## Open questions
- Laya vs Jev accuracy on our PDLC decisions at matched questions: not measured anywhere for our data.
- Actual CPU latency p50/p95 for a 10 to 30 question battery at 1024 tokens on our build machines: not stated.
- Does the English (ModernBERT-large, 512) or Multilingual (mmBERT-base, 1024) checkpoint do better on English engineering text given the window trade-off? Not stated.
- Can a fine-tuned Laya checkpoint (own decisions) be served through the same endpoint without code changes? Code suggests a local folder works; untested.

## Grading and labels
- Directness: high, primary docs plus implementing code at a pinned commit.
- Control: unknown, no comparative measurement at all.
- Independence: medium, integrator is not the model author (inference), but this is vendor documentation.
- Reproducibility: high for the API contract (pinned code, open licences); nothing quantitative to reproduce.
- Applicability: medium, local and cheap, but the token window blocks long artifacts.
- Pillars: R9 primary; R7 (wire compatibility and its gaps), R8 (data stays local, keyless restrictions), R4 (thresholds on probabilities) secondary.
- Stage: none (the source is not stage-specific; candidate stages listed above are inference).
- Tags: see frontmatter.
- Beliefs: supports B14 (calibration claimed, not shown; docs themselves say thresholds do not transfer and must be refit locally). No contradiction.

## Origin chain
X post 2104819623824634287 (@realfxw, Chinese; content from triage brief, not re-fetched) -> https://unsloth.ai/docs/models/decision-laya (tables "Recommended Settings", "Question types", section "Migrating from Jev") -> github.com/unslothai/unsloth @ 6c20f0fac752a1ec64537575873fa7f835d348dd: `studio/backend/routes/systemone.py` (limits, validation, errors), `studio/backend/core/systemone/catalog.py` (checkpoints, aliases, byte sizes), `studio/backend/core/systemone/laya_runtime.py` (device, precision, truncation, response fields), `studio/backend/vendor/laya_manifest.json` (laya 0.3.5, Apache-2.0), `studio/backend/vendor/laya/common.py` line 210 (confidence formula) -> huggingface.co/api/models/convaiinnovations/laya (license apache-2.0). Independence: the post relays the vendor docs; the docs and code are from the same vendor; no third-party measurement.
