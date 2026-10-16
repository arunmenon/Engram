---
schema_version: 1
artifact_id: N-SURVEY-20260927-01
artifact_type: note
producer: triage
run_id: survey-20260927T044739Z-8de9
created_at: 2026-09-27T04:53:14Z
idempotency_key: note:survey:arxiv:2601.15322
input_refs: []
pillar_primary: R1
pillar_secondary: [R6]
beliefs_affected:
  supports: []
  contradicts: [B1]
  note: contradicts only the "sufficient" clause of B1 when "reproduce a decision" means re-deriving it by re-running the model on the retained evidence; retaining the model's recorded output restores sufficiency
evidence:
  directness: 4
  control: 3
  independence: 4
  reproducibility: 4
  applicability: 3
  scale: 1-5, 5 best
source_url: https://arxiv.org/abs/2601.15322
found_via: survey
---

# Replayable Financial Agents: A Determinism-Faithfulness Assurance Harness for Tool-Using LLM Agents (DFAH)

- **URL:** https://arxiv.org/abs/2601.15322 (HTML read at https://arxiv.org/html/2601.15322)
- **Type:** paper
- **Author / org:** Raffi Khatchadourian, IBM
- **Date:** submitted 7 Mar 2026 (per alphaXiv listing)
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, R1 question "does retaining served evidence suffice to reproduce a decision?"
- **Relevance to a memory stack:** high. It measures how often a tool-using agent reaches the same decision when re-run at T=0 on the same case, which is exactly the gap between "we kept what was served" and "we can reproduce the decision".

## TL;DR
- 4,700+ agentic runs, 7 models, 4 providers, 3 financial benchmarks with 50 cases each, all at T=0.0.
- Frontier models reach the same final decision across replays only 64 to 94 % of the time on the two valid benchmarks (the abstract's "50-96%" includes the voided portfolio table); tool-sequence-plus-arguments identity ("signature determinism") is often much lower (20 to 70 %).
- Decision determinism and accuracy are "not detectably correlated (r = -0.11, 95% CI [-0.49, 0.31], p = 0.63, n = 21 configurations)". The author stresses this does not establish independence.
- Hosted APIs do not guarantee seed determinism; the same model (granite-3.3) behaves differently on Ollama vs watsonx.
- Faithfulness is scored with a lexical/entity heuristic, not an LLM judge ("using an LLM to evaluate faithfulness defeats the purpose of an audit harness").

## What it claims / describes
A harness that re-runs each case N times and reports three things: decision determinism, signature determinism (identical tool names and arguments) and evidence-conditioned faithfulness (claims aligned with retrieved evidence). Runs per case: 3 for API models, 8 for local models. Seed 42 is requested where supported; the Anthropic API has no seed parameter.

## Numbers

Definitions, quoted: "DecDet(q)=1/N sum 1[d(i)=d(1)]" (fraction of runs with identical final decisions); "SigDet(q)" the fraction of runs with identical tool sequences and arguments. Evidence grounding: token-level Jaccard >= 0.6 plus entity matching; numeric claims require exact match.

Table 4, Compliance Triage (verbatim values):

| Model | Tier | Dec.Det % | Sig.Det % | Acc % | Tools/Run |
|---|---|---|---|---|---|
| qwen2.5:7b | Tier 1 | 100.0 | 100.0 | 38.0 | 2.9 |
| gpt-oss:20b | Tier 1 | 86.0 | 92.0 | 34.8 | 4.0 |
| gemini-2.0-flash | Frontier | 68.0 | 66.0 | 52.0 | 3.8 |
| gemini-2.5-pro | Frontier | 68.2 | 40.9 | 40.2 | 3.3 |
| claude-sonnet-4 | Frontier | 82.0 | 44.0 | 33.3 | 4.6 |
| claude-opus-4 | Frontier | 72.0 | 44.0 | 68.7 | 4.2 |
| granite3.3 | Tier 1 | 100.0 | 100.0 | 34.0 | 0.0 |

Table 6, DataOps Exception:

| Model | Tier | Dec.Det % | Sig.Det % | Acc % | Tools/Run |
|---|---|---|---|---|---|
| qwen2.5:7b | Tier 1 | 94.0 | 94.0 | 42.2 | 4.1 |
| gpt-oss:20b | Tier 1 | 84.0 | 74.0 | 43.2 | 3.4 |
| gemini-2.0-flash | Frontier | 94.0 | 70.0 | 34.7 | 3.5 |
| claude-sonnet-4 | Frontier | 84.0 | 26.0 | 14.0 | 5.0 |
| claude-opus-4 | Frontier | 64.0 | 20.0 | 24.0 | 4.9 |

Table 5 (Portfolio Constraint) also reports frontier Dec.Det 50.0 to 96.0 %, but the paper says the portfolio fixture is "excluded from current evidence because of documented inconsistencies". Treat Table 5 as void.

| Metric | Value | Caveat |
|---|---|---|
| Correlation determinism vs accuracy | r = -0.11315, p = 0.62531, n = 21 | "A nonsignificant test does not establish equivalence or independence." |
| Validation overhead | up to 3.7x for Tier 3 vs Tier 1 | tier definitions not re-read |
| Cost, latency | not stated | |

## Mechanism details you could implement
- Report determinism at two levels: final decision and full tool signature. They diverge; several configurations have higher decision unanimity than tool-sequence unanimity.
- Score evidence grounding deterministically (Jaccard >= 0.6, exact numeric match) so the audit does not itself add model nondeterminism.
- Record provider, not just model id: same weights on different serving stacks differ.

## Limitations, caveats, counter-evidence
- Synthetic fixtures, 50 cases per benchmark; author says the values "do not support model rankings".
- granite3.3 has Tools/Run 0.0, so its 100 % determinism is trivially reached by not acting (inference).
- 3 replays per API case is a small N for a unanimity rate; a 3-run unanimity rate is an optimistic bound on true agreement (inference).
- Models are 2025-era (Claude 4, Gemini 2.5); current models not tested.

## Takeaways for tuning a memory stack
- A ledger that keeps the served briefing, source positions and versions lets a reviewer see what the agent saw. It does not let them re-derive the decision: re-running a frontier model at T=0 on the same inputs left frontier models without a unanimous final decision in 6 to 36 % of Compliance and DataOps cases (Dec.Det 64.0 to 94.0 %).
- For B1: "sufficient" holds only if the receipt also stores the model's output, model id, provider and sampling parameters, and "reproduce" is defined as "show inputs and recorded output", not "re-run". P0's replay contract should say which of the two it guarantees.
- A deterministic, non-LLM grounding check is a viable audit primitive for "was the decision supported by the served evidence".

## Open questions
- Does determinism change when the served evidence is a fixed memory briefing rather than live tool calls (fewer nondeterministic boundaries)?
- Current model generations and self-hosted batch-invariant inference are untested here (see N-SURVEY-20260927-02).
