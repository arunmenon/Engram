---
schema_version: 1
artifact_id: N-20260930-20
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105152056382345544", "file_id": null, "sha256": null}, {"artifact_id": "post:2105184513496326614", "file_id": null, "sha256": null}, {"artifact_id": "post:2105160587407728985", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:ollama.com/blog/ollama-now-supports-jev-style-decision-models
claim_cluster: url:ollama.com/blog/ollama-now-supports-jev-style-decision-models
feeds: ["decision", "memory"]
primary_source: https://ollama.com/blog/ollama-now-supports-jev-style-decision-models
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R9
pillar_secondary: ["R7"]
memory_stage: none
priority: 2
tags: {"mechanism": ["local /v1/systemone endpoint", "choice, noul and score questions", "probabilities plus separate confidence field", "TypeSafe SDK compatibility"], "workload": ["ticket triage", "model routing", "tool-call harm check"], "lifecycle_stage": ["routing", "safety"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium", "control": "low", "independence": "low", "reproducibility": "medium", "applicability": "medium"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["An open-weight 9B decision model served locally is within 0.3 points of hosted Jev 1.13 on a public 13-dataset benchmark, so self-hosting the decision layer is a practical option to test on our own decisions"]}
claim_correction: none
---

# Ollama now supports Jev-style decision models: a local /v1/systemone endpoint with Nimble (Bespoke Labs) and Tev1 (Together AI)

- **URL:** https://ollama.com/blog/ollama-now-supports-jev-style-decision-models
- **Type:** vendor blog
- **Author / org:** Ollama
- **Date:** 2026-09-29
- **Retrieved:** 2026-09-30 (local copy of the page: repos/_src_ollama_decision.html). The linked model pages (ollama.com/library/nimble) and the benchmark document (github.com/bespokelabsai/nimble, docs/PUBLIC_BENCHMARKS.md) were not read.
- **Cited by evidence:** https://x.com/ollama/status/2105152056382345544 (@ollama, 652 likes), https://x.com/LilithDatura/status/2105184513496326614 (@LilithDatura, quotes 91 ms and 75.7% vs 76.0%), https://x.com/bygregorr/status/2105160587407728985 (@bygregorr, reply: model routing is the weakest case locally because of cold starts). Both digests of 2026-09-30.
- **Relevance to a memory stack:** medium. CTO priority 2 asks whether we can run a decision model ourselves so memory text stays in-house. This is the first mainstream local runtime to ship the Jev request shape, with a stated accuracy gap to Jev and a latency figure.
- **New relative to existing notes:** Nimble was already noted as the model behind djev (github-djev-deterministic-jev-server.md, served on SGLang) and Tev1 in vendor-together-tev1-4b-experimental.md. New here: a stock endpoint in Ollama 0.35, the 13-dataset comparison chart including Tev1 0.8B, and the 91 ms figure on a laptop.

## TL;DR
- "This new API is available as of Ollama 0.35 by using the new `/v1/systemone` endpoint. Send text as `state` with a set of named questions, and a model running on your machine answers them all in one request."
- Three models: `nimble` ("open-source 9B parameter decision model developed by Bespoke Labs"), `tev1` ("an experimental 4B decision model from Together AI"), `tev1:0.8b`.
- Accuracy chart: "Jev 1.13 76.0%, Nimble 9B 75.7%, Tev1 4B 73.3%, Tev1 0.8B 63.5%", "Mean accuracy across 13 public data sets with human labels, covering 3,880 decisions."
- Latency: "Nimble 9B averaged 91ms per decision in the Pac-Man example below when running locally on an M5 Max."
- The Jev figure was not run by Ollama: "Jev 1.13 is from Bespoke Labs' published run on the same decisions." The post by @LilithDatura repeats the chart correctly. No claim correction.

## What it claims / describes

**Request shape (verbatim from the page).**
```text
curl http://localhost:11434/v1/systemone -d '{
  "model": "nimble",
  "state": {"ticket": "I was charged twice. Please refund the extra payment."},
  "questions": {
    "team": {"type": "choice", "instructions": "Which team should handle this ticket?",
             "criteria": {"billing": "Payments and refunds", "technical": "Bugs and integrations", "other": "None of the above"}},
    "refund": {"type": "noul", "instructions": "Does the customer explicitly ask for a refund?"},
    "urgency": {"type": "score", "instructions": "How urgent is this ticket?", "criteria": ["Routine", "Soon", "Urgent"]}
  }
}'
```
(whitespace condensed).

**Response shape (verbatim values).**
```text
"team":    {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.985, "technical": 0.012, "other": 0.003}, "confidence": 0.922}
"refund":  {"type": "noul", "noul": 0.997}
"urgency": {"type": "score", "score": 0.815, "legend": {"0": "Routine", "1": "Soon", "2": "Urgent"},
            "probabilities": {"0": 0.378, "1": 0.429, "2": 0.193}, "confidence": 0.046}
"usage":   {"input_tokens": 841, "output_tokens": 4}
```
`state` may be a string or a JSON object. Criteria values may be null (label only) or a description. The page says requests can be made "via `curl` or via TypeSafe's official Python SDK".

**Other examples on the page.** Model routing: state "Design a sharded database schema for a payments ledger.", choice between `gemma4` ("Small model") and `kimi-k3` ("Large model"), answer `kimi-k3` with probabilities 0.151 and 0.849 and `"confidence": 0.388`. Tool-call harm: state `run_shell(command="rm -rf ~")`, noul 0.996. The example panels show 138 to 141 ms.

**Stated benefits.** "No additional costs", "Lower latency when run locally", "Three new decision models available today via Ollama".

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Mean accuracy, Nimble 9B | 75.7% | Jev 1.13 76.0% | chart "Bespoke Labs public benchmarks": 13 public data sets with human labels, 3,880 decisions | benchmark built by Nimble's maker; Jev row is Bespoke's published run, not re-run by Ollama |
| Mean accuracy, Tev1 4B | 73.3% | Jev 1.13 76.0% | same | "Nimble and Tev1 were evaluated on Ollama" |
| Mean accuracy, Tev1 0.8B | 63.5% | Jev 1.13 76.0% | same | |
| Latency per decision, Nimble 9B | "91ms per decision" average | none | Pac-Man demo, local on an M5 Max | one demo, short states; not a benchmark |
| Example request latency | 138 to 141 ms | | three example panels | illustrative |
| Tokens in the three-question example | input 841, output 4 | | page example | unlike TypeSafe's "output is free" framing, output tokens are reported as nonzero |
| Quantisation, context length, licence, memory footprint | not stated on this page | | | |
| Calibration (ECE or similar) | not stated | | | |

## Mechanism details you could implement
- A local decision service can be swapped behind the same client as hosted Jev: same `state` plus `questions` request, same three question types, same answer fields. Point the TypeSafe SDK at the local base URL (the page shows an SDK tab; its contents were not read).
- The response separates `probabilities` from `confidence`. In the routing example the winning probability is 0.849 and confidence is 0.388; in the score example the top level has 0.429 and confidence is 0.046. Branch on the probabilities or on a locally fitted threshold, not on `confidence` alone (inference from the page's own examples; consistent with note blog-jev-calibration-two-confidence-numbers.md).
- Include an explicit "None of the above" option in a routing choice when abstaining is allowed; the page's own example does.

## Limitations, caveats, counter-evidence
- The accuracy comparison uses the benchmark suite published by Bespoke Labs, the maker of Nimble. The suite document was not read this run; dataset list and per-dataset scores are unknown here.
- Accuracy only; no calibration measurement for any of the four models.
- The 91 ms figure is from a game demo on a top-end laptop; latency on memory-sized states (several thousand tokens) is not given.
- Reply from @bygregorr: local models each hold their own KV cache, "so you still pay cold-start cost on every routed call"; an opinion, not measured.
- Counter-evidence on small open-weight models for memory decisions: Nowledge Mem (N-20260930-12) found that no local model it tested (encoders and a 0.8B LoRA model) met its bar; it did not test Nimble.

## Takeaways for tuning a memory stack
- The self-host arm of a Jev comparison no longer needs a custom server: Ollama 0.35 exposes the same request shape locally.
- Expect a 9B model to be needed for near-parity on public sets; the 0.8B model is 12.5 points behind.
- Fit thresholds per model on our own decisions; nothing on this page says the probabilities are calibrated.
- Measure local latency at our state sizes before assuming the 91 ms figure.

## Open questions
- How do Nimble and Tev1 do on memory decisions (store or skip, replaces or not, relevant or not) rather than public classification sets? Unknown.
- What hardware and quantisation does 91 ms assume beyond "M5 Max"? Not stated.
- Is the endpoint deterministic across runs and batch sizes (the djev note raises this for SGLang)? Not stated.

## Grading and labels
- **Directness: medium.** The vendor page shows the API and a chart; the underlying per-dataset results were not read.
- **Control: low.** One aggregate accuracy per model; the Jev row comes from a different party's run.
- **Independence: low.** Runtime vendor plus the model maker's benchmark.
- **Reproducibility: medium.** Models are pullable and the benchmark suite is linked; no commit or version pins on the page beyond "Ollama 0.35".
- **Applicability: medium.** Directly relevant to the self-hosting goal; tasks are generic classification.
- **Strength:** vendor-benchmark.
- **Pillars:** R9 primary (open-weight System One models, cost, self-hosting). Secondary R7 (a second implementation of the same interface: a swap test becomes possible). Memory stage: none. Priority 2.
- **Beliefs:**
  - B14 supports: the examples show `confidence` diverging from the top probability, and no calibration evidence is offered.
  - Would create: a locally served open 9B decision model is within 0.3 points of Jev 1.13 on a public benchmark.
- **Contradiction rows:** none.

## Origin chain
- Post https://x.com/ollama/status/2105152056382345544 -> https://ollama.com/blog (index) -> post of 2026-09-29 -> accuracy chart description and figcaption, latency sentence, request and response examples -> this note.
- Independence: Ollama (runtime), Bespoke Labs (Nimble and the benchmark suite), Together AI (Tev1). The Jev figure originates with Bespoke Labs. Overlaps with the djev note (same model, Nimble) and the JevBench v1.5 note (open models near Jev 1.13), which use different harnesses.
