# TypeSafe System One API (Jev): Noul request structure, full request/response schema, confidence, calibration and re-ranking docs

- **URL:** https://docs.typesafe.ai/primitives/noul#request-structure (also read: https://docs.typesafe.ai/api, /primitives, /confidence, /models, /model-jaggedness/jev-1.13, /introduction/machine-learning-primer, /patterns/confidence-routing, /concepts/state, /cookbooks/rerank_typesafe, /cookbooks/classifying_rag_passages, /cookbooks/consistency_noul_cookbook, /sdk/python/api/constants, index at /llms.txt)
- **Type:** vendor docs
- **Author / org:** TypeSafe AI (typesafe.ai)
- **Date:** undated pages; models page lists `jev-1.13.0` as current; jaggedness page "Last reviewed 2026-09-17"; consistency cookbook sampled 2026-09-11.
- **Retrieved:** 2026-09-26 (local copy: /private/tmp/claude-501/-Users-arunmenon-projects-localai-signals/3f9824a6-23ac-471e-adc7-a1ca0ec806fd/scratchpad/jevdocs/, raw `.md` pages plus `.clean.txt` with JSX stripped)
- **Cited by evidence:** reference for all Jev-related evidence: Decision models as the memory control plane (2026-09-24 Vectorizeio; 2026-09-25 ethanwalkerman), Memory that updates on read (2026-09-24 sergeonsamui, hippo-memory's opt-in Jev reranker), Typed-decision tier displacing LLM calls (2026-09-25 metalagman)
- **Relevance to a memory stack:** high, as the exact wire contract any Jev-based write gate, recall gate or reranker would use, plus the vendor's own guidance on thresholds, calibration and failure modes.

## TL;DR
- One endpoint: `POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer <API_KEY>`, body `{state, model, questions}`. `questions` is a map of caller-chosen ids to typed questions (`noul`, `choice`, `score`). Ids are "not sent to the model".
- Noul returns only `{"type":"noul","noul": <P(yes)>}`: no rationale, no confidence field. Choice and Score also return `probabilities` and `confidence`.
- All questions in one request share one `state` and are evaluated in parallel; the docs say extra questions barely change latency and cost only their tokens. Price for `jev-1.13.0`: USD 0.042 per million input tokens, output tokens free.
- Calibration is claimed via training (RLCD, "reinforcement learning for calibrated decisions"), with the standard definition (0.8 happens about 80% of the time). No calibration metric (ECE, Brier, reliability diagram) appears on any page read.
- Re-ranking cookbook: one Noul per (query, candidate) pair over a BM25 top-30 on CLERC legal (40 queries): top-1 5% -> 18%, top-5 15% -> 35%, top-10 38% -> 62%, 1,200 calls for USD 0.0645 (on `jev-1.12`).

## What it claims / describes

### Endpoint and request body (API reference)
```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```
Top-level fields, all required:
| field | type | meaning |
|---|---|---|
| `state` | string, object or array | "The content to evaluate." Text only; objects/arrays of text values allowed. |
| `model` | string | e.g. `"jev-latest"`; alias or versioned id such as `jev-1.13.0` |
| `questions` | map<string, Question> | caller-chosen ids; answers come back under the same ids; "The key is not sent to the underlying model and is not used in inference." |

### Noul question ("Request structure" section, the cited anchor)
Fields, verbatim from the page:
* `type`: Always `"noul"`.
* `instructions`: "The yes/no question the model answers, or a statement for it to judge." Type string, object or array.
* `criteria`: "Optional. An object with `true` and `false` descriptions of what a yes and a no mean." Each of `true` / `false` may be string, object or array.

Example request from the page:
```json
{
  "state": "I have asked three times now. Can I please just talk to a real person?",
  "model": "jev-latest",
  "questions": {
    "is_human_escalation": { "type": "noul", "instructions": "Is the customer asking for a human agent?" },
    "is_repeat_contact": {
      "type": "noul",
      "instructions": "Has the customer contacted support about this before?",
      "criteria": {
        "true": "Mentions a prior attempt, ticket, or that they have asked before",
        "false": "No sign of any previous contact"
      }
    }
  }
}
```
Response:
```json
{
  "model": "jev-1.13.0",
  "answers": {
    "is_human_escalation": { "type": "noul", "noul": 0.99 },
    "is_repeat_contact":   { "type": "noul", "noul": 0.93 }
  },
  "usage": { "input_tokens": 360, "output_tokens": 39 }
}
```
Structured instructions (object form) let code put data next to the question and reference it by name in backticks:
```json
"instructions": {
  "potential_duplicate": { "name": "Jon Smith", "location": "Oakland, CA", "last_employer": "Google" },
  "question": "Is the resume for the same person as `potential_duplicate`?"
}
```
(Returned 0.74 for a same-person record with a spelling variant, 0.09 and 0.08 for two non-matches.) This is the documented pattern for dedup against N candidate records in one request, with question ids like `same_as_record_18`.

### Choice question
* `type`: `"choice"`; `instructions` (string/object/array, required); `criteria`: required map<option, string|object|array|null>, "a maximum of 255 options per Choice".
* Answer: `{"type":"choice","choice":"billing","probabilities":{"billing":0.88,"technical":0.12,"sales":0.0},"confidence":0.81}`. `choice` is "The highest-probability option"; probabilities sum to 1.

### Score question
* `type`: `"score"`; `instructions` required; `criteria`: required ordered array of level descriptions, "at least two levels; the API accepts up to 10".
* Answer: `{"type":"score","score":1.05,"legend":{"0":"Calm","1":"Frustrated","2":"Very angry"},"probabilities":{"0":0.0,"1":0.95,"2":0.05},"confidence":0.92}`. `score` is "The probability-weighted answer across the levels; can land between levels."

### Response body
| field | type | required |
|---|---|---|
| `model` | string, the versioned model that answered (e.g. `jev-1.13.0` when `jev-latest` was requested) | yes |
| `answers` | map<question id, Answer>, each with `type` matching the question | yes |
| `usage` | `{input_tokens: int, output_tokens: int}` | yes |

### Errors
| status | meaning |
|---|---|
| 401 | missing or invalid API key |
| 422 | body failed validation; body names the offending field |
| 429 | rate limit exceeded; back off |
| 529 | overloaded; retry after a short delay |
"retry the request with exponential backoff"; SDKs do this by default and honor `retry-after`.

### Other endpoint
`GET https://api.typesafe.ai/v1/models` lists names (currently aliases) with description and release date. Versioned ids are accepted even if not listed.

### Models page (jev-1.13.0)
| item | value |
|---|---|
| Price | USD 42 per billion input tokens (USD 0.042 per million); output tokens free |
| Rate limits | 250,000 tokens per second, 1,200 requests per minute; "adjusting dynamically ... can change without notice" |
| Context | 64k tokens per request (state plus all questions); 32k tokens for state plus the single longest question |
| Input | text only |
| Aliases | `jev-latest` -> `jev-1.13.0` (stable); `jev-preview` -> `jev-1.13.0` (no preview build currently) |
Guidance: "If you have tuned confidence thresholds against a specific version, pin that version's ID instead of the alias." Jev is "not fine-tuned or LoRA-adapted with customer data ... the same weights serve every account." English is the primary language.

### SDK constants (Python `typesafe_sdk.constants`)
`API_KEY_ENV = 'TYPESAFE_API_KEY'`, `BASE_URL_ENV = 'TYPESAFE_BASE_URL'`, `DEFAULT_MODEL_ENV = 'TYPESAFE_DEFAULT_MODEL'`, `LOG_LEVEL_ENV = 'TYPESAFE_LOG_LEVEL'`, `DEFAULT_BASE_URL = 'https://api.typesafe.ai'`, `DEFAULT_MODEL = 'jev-latest'`. Python call: `client.system_one(model=..., state=..., questions={...})`, read `response.answers[id].noul`.

### Confidence
- Noul: "There is no separate `confidence` value for a Noul ... the single `noul` value describes it completely."
- Choice/Score: `confidence` "is a statistic computed from the probability distribution", 0 to 1; flatter distribution means lower confidence. The formula is not stated in prose; the page's interactive widget computes Choice confidence as `max(0, min(1, (n * p_max - 1) / (n - 1)))` for n options (from the page's embedded JavaScript, inference that the API uses the same formula).
- Recommended three-path policy: high confidence act, medium confirm or review, low do not act. Examples use a 0.5 floor with 0.9 for destructive actions (confidence page) and 0.6 floor with 0.85 for a high-stakes action (confidence-gated routing pattern).

### Calibration (AI primer)
RLCD output contract: "The model does not generate text. It returns decisions and probabilities. Higher probability should correspond to a greater chance that the answer is correct." "Outcomes assigned a probability of `0.8` should occur about 80% of the time." "These rates describe groups of predictions, not a guarantee about any single answer." No measured calibration numbers are given on the pages read.

### Re-ranking cookbook (the directly linked Jev reranking page)
Setup: CLERC legal retrieval, 170 rows pooled into 3,565 passages, 40 evaluation queries, BM25 (`bm25s`, English stopwords) top 30 per query, model `jev-1.12`, one Noul per pair, state `{"query_excerpt": ..., "candidate_passage": ...}`, 12 worker threads, sort descending by `noul`. Question used:
```text
instructions: "The query excerpt comes from a US federal court opinion and was written immediately around a citation to a precedent; the citation itself has been removed. Could the candidate passage be from that cited precedent, does it establish the specific legal proposition the query excerpt invokes at its citation point?"
true:  "The candidate passage states or establishes the specific rule, standard, holding, or fact pattern that the query excerpt attributes to its removed citation."
false: "The candidate passage is merely on a similar topic or doctrine; it does not supply the specific proposition the query excerpt relies on."
```
Note the page says a real application would ask several questions about the same pair in one call.

### Classifying RAG passages cookbook
Four Nouls per retrieved passage (`is_relevant`, `contains_answer_evidence`, `contradicts_query_premise`, `contains_prompt_injection`), routed in code, first match wins, with thresholds held in one dict:
```python
THRESHOLDS = {
    "injection_max": 0.70,  # above this the passage never reaches the prompt
    "contradicts_min": 0.70,
    "relevant_min": 0.45,
    "evidence_min": 0.55,
}
```
Model `jev-1.12`. One request per passage.

### Self-consistency (Noul) cookbook
One auto-insurance claim, 14 Noul questions, 15 runs each, fresh `uid` per call. TypeSafe mean per-question probability standard deviation 0.0102, "below all LLM probability conditions here", yet its `covered` answer spanned 0.43 to 0.53, crossing a 0.5 threshold. Recommends an uncertainty band 0.30 to 0.70 routed to human review.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Price | USD 0.042 / M input tokens, output free | n/a | jev-1.13.0 models page | rate limits and pricing may change |
| Rate limit | 250k tok/s, 1,200 req/min | n/a | models page | "adjusting dynamically" |
| Context | 64k per request; 32k state + longest question | n/a | models page | accuracy drops with irrelevant state (jaggedness) |
| Choice options max | 255 | n/a | API ref | |
| Score levels | 2 to 10 | n/a | API ref | |
| Rerank top-1 | 18% | 5% BM25 | CLERC, 40 queries, top-30 shortlist, jev-1.12 | small n; vendor-run; shortlist recall was 100% |
| Rerank top-5 | 35% | 15% | same | |
| Rerank top-10 | 62% | 38% | same | |
| Rerank cost | 1,200 calls, 1,536,002 input tokens, USD 0.0645 | n/a | same | |
| Batching 13 questions vs 13 calls | 11.5x cheaper, 9.6x faster (primitives page); 12.2x cheaper, 10.0x faster (llms.txt index) | separate calls | GDPR article | two pages disagree |
| Self-consistency stdev | 0.0102 mean per-question | all LLM conditions higher | 14 Nouls x 15 runs, jev-latest -> jev-1.13.0 | one claim only |
| Latency / cost per 14-question call | 111 ms, USD 0.000043 | claude-haiku-4-5 t=0: 1780 ms, USD 0.001798 (16.0x / 42.2x); opus-4-8 reasoning 13,886 ms, USD 0.034275 | same | historical price assumptions per the page |
| Noul examples | 0.02 ("Thanks, that fixed it!") ... 0.40 ("Are you a bot?") ... 0.99 | n/a | is_human_escalation | illustrative |
| Calibration error | not stated | | | no ECE/Brier on pages read |

## Mechanism details you could implement
- **Write gate / recall gate call:** one request per memory item (or per episode) with several Nouls keyed by stable ids, e.g. `{"should_store": ..., "is_new_fact": ..., "contradicts_existing": ...}`. The docs' checklist guidance: "one question per condition, and the code decides what the combination means."
- **Dedup against existing memories:** put the new item in `state`, and one Noul per candidate existing memory with structured instructions `{ "existing_memory": {...}, "question": "Does the new item state the same fact as `existing_memory`?" }`, ids `same_as_mem_<id>` (pattern from the resume dedup example; threshold 0.7 used there).
- **Reranking recalled memories:** state `{query, candidate}`, Noul with explicit `true`/`false` criteria that separate "answers the query" from "on a similar topic", sort by `noul` (no threshold). For an abstain decision use an absolute Noul per candidate, not a Choice, because "the Choice is relative ... while each Noul is absolute and can be low for all of them" (jaggedness page).
- **Thresholding:** "Use 0.5 when yes and no are equally easy to act on. Raise it when acting on a false yes is expensive ... Lower it when missing a true yes is expensive." Middle band to review, e.g. `NO = 0.2, YES = 0.8` in the Noul page, 0.30 to 0.70 in the consistency cookbook.
- **Pin the model version** (e.g. `jev-1.13.0`) once thresholds are tuned; log the returned `model`.
- **Question writing rules** (Noul page): one condition per Noul; phrase so a high value means yes (avoid "free of X"); add `criteria` when the boundary is subtle and A/B with and without; statements work as well as questions.

## Limitations, caveats, counter-evidence
From the jaggedness page (jev-1.13), verbatim headings and advice:
1. Literal reading: "answers the question you wrote, not the one you meant."
2. Math and numbers, counting: "does not count reliably"; score levels "weak in numerical calibration".
3. Date and time comparison: "reads dates as text, not as ordered quantities" (relevant to temporal memory: do recency and ordering in code).
4. Indirection: multi-hop questions lose accuracy.
5. Large state full of irrelevant detail: "Jev suffers from context rot"; filter before sending.
6. Adversarial content: "State is data, and `jev-1.13` does not treat it as hostile by default" (memory contents can steer the gate, inference).
7. Contradictory instructions and criteria.
8. Structural invariants not guaranteed: `refund` 0.72 and `not_refund` 0.47 on the same ticket (sum 1.19); a Noul 0.22 vs a yes/no Choice 0.01 for the same question. "Don't carry a threshold tuned on a Noul over to a Choice."
9. Generation: "not trained to generate text"; extraction must come from regex or a generative model, with Jev choosing.
Other caveats: calibration is asserted, not measured on these pages; cookbook numbers are vendor-run on small sets (40 queries, one claim); rate limits are unstable; English-first.

## Takeaways for tuning a memory stack
- Jev fits the *decision* slots of a memory pipeline (store or drop, is duplicate, is superseded, is relevant to this query, should recall at all), never the *content* slots (writing the memory, summarizing). Every repo in this batch that uses it (Beacon, LintPal) keeps text generation elsewhere.
- For reranking recalled memories, the cookbook recipe is BM25 or embedding shortlist, then one Noul per pair sorted by probability; the reported lift is large at top-1 but on a 40-query legal set, so benchmark on LongMemEval or LoCoMo yourself.
- Put multiple gate questions in one request per item to keep cost near one call; at USD 0.042 per million input tokens, the dominant cost is state size, so keep the state to the item plus only the context each question needs (also avoids the context-rot failure).
- Do temporal logic (which memory is newer, validity windows) in code, not in the Noul; use a Choice over enumerated date parts if extraction is needed.
- Use a review or "defer" band around 0.5 rather than a single threshold; the vendor's own consistency run shows about 0.1 of run-to-run spread on a borderline question.
- Pin `jev-1.13.0` in production gates; `jev-latest` can move under tuned thresholds.

## Open questions
- Measured calibration (ECE or reliability curves) of Noul outputs on memory-type questions: not stated.
- Whether per-question accuracy degrades when many Nouls share one request: the docs say answers do not change with batching (parallel questions cookbook), but that page was not fetched here; only its summary lines were read.
- Exact server-side limits on the number of questions per request: not stated on the pages read (LintPal caps itself at 128 per batch by default, 1024 hard).

---
