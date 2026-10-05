---
schema_version: 1
artifact_id: N-SURVEY-20260928-04
artifact_type: note
producer: triage
run_id: survey-20260928T055608Z-7419
created_at: 2026-09-28T06:30:00Z
idempotency_key: note:survey:arxiv:2609.17648
input_refs: []
pillar_primary: R8
pillar_secondary: [R7]
beliefs_affected:
  supports: [B25]
  contradicts: []
evidence:
  directness: high (separates compromise of the judging agent from unsafe execution, with and without an authorization layer outside the LLMs)
  control: medium (component-level ablation; 3 seeds x 60 tasks; authorization ablation single seed n=60)
  independence: medium (academic; least-privilege policy written by the same group)
  reproducibility: low (code URL not stated)
  applicability: medium (four-agent LangGraph pipeline, 13 action types, one model gemma4:31b; not a coding agent)
source_url: https://arxiv.org/abs/2609.17648
found_via: survey
---

# Trust propagation and structural containment in Multi-agent LLM pipelines

- **URL:** https://arxiv.org/abs/2609.17648 (HTML read at https://arxiv.org/html/2609.17648)
- **Type:** paper (IEEE CARS 2026)
- **Author / org:** Tanzim Hossain Safin, Sharif Noor Zisad, Swakkhar Shatabda, Ragib Hasan
- **Date:** 2026-09-15
- **Retrieved:** 2026-09-28 (local copy: out/log/h-2609.17648.html)
- **Cited by evidence:** top-down survey, R8 question 3 (B25)
- **Relevance to a memory stack:** medium-high, it measures exactly B25's claim: an agent that reads poisoned memory can be fully fooled while execution is still contained by authority that does not come from the evidence

## TL;DR
- Supervisor (deterministic), Researcher, Validator, Executor in LangGraph with shared typed state; LLM agents gemma4:31b-cloud via Ollama at temperature 0.
- Shared-memory poisoning (forged approval) reaches execution in every undefended trial (Unsafe Action Rate 100 %).
- With the authorization layer (task-bound HMAC-signed single-use tokens plus an independently verified policy oracle), the Validator is still bypassed in 100 % of attacked trials (JBR) but Unsafe Action Rate is 0 %.
- If the attacker holds the signing secret, the signed token alone is no better than no defense; the policy oracle alone reproduces full containment.
- Indirect injection via a retrieved document with a fabricated approval is blocked, but at 49.1 % false-positive rate; an Observer that strips fabricated approval claims cuts FPR to 7.4 % and raises legitimate completion from 50.9 % to 92.6 %.

## What it claims / describes
Authority is checked at the inter-agent boundary by components outside the LLMs: a token bound to task and scope (HMAC, single-use nonce) and a policy oracle that evaluates the requested action against a policy ("corpus" policy from task labels, or a hand-written least-privilege allowlist). Judgment Bypass Rate JBR = Nb/Na, where Na is gold-unsafe attack-injected trials and Nb those where the Validator's genuine review was skipped or bypassed: it measures compromise at the attacked agent, not at the action.

## Numbers
| Attack | Tier | UAR | FPR | JBR | n |
|---|---|---|---|---|---|
| Memory poisoning | T0 (no authorization) | 100.0 % | 0.0 % | 100.0 % | 180 |
| Memory poisoning | T1 (authorization) | 0.0 % | 0.0 % | 100.0 % | 180 |
| Agent hijacking (doc injection) | T0 | 0.0 % | 59.3 % | 0.0 % | 180 |
| Agent hijacking | T1 | 0.0 % | 49.1 % | 0.0 % | 180 |

Corpus vs independent least-privilege policy (T1): memory FPR 0.0 / 0.0, F1 1.00 / 1.00; hijack FPR 49.1 / 46.3 %, F1 0.74 / 0.74.
Observer on hijacking: FPR 49.1 % to 7.4 %; legitimate task completion 50.9 % to 92.6 %; F1 0.74 to 0.95; JBR 0.0 % to 4.2 %; in-pipeline detection 97.2 %; removal on clean content 0.0 %; UAR 0 % in both.
60 tasks = 36 safe, 24 unsafe; hijack FPR 95 % interval across seeds [28.1 %, 70.0 %].

## Mechanism details you could implement
- Bind every executable action to a task-scoped, single-use, signed grant issued outside the model, and evaluate it against a policy the evidence cannot edit. A signature only proves origin; the policy check is what contains an attacker who can sign.
- Report JBR (was the reviewing agent fooled?) separately from UAR (did an unsafe action happen?).

## Limitations, caveats, counter-evidence
- Injected approvals are explicit and conspicuous; adaptive attackers untested.
- Single model, single framework, 60 tasks, 13 action types; policy authored by the same group.
- The large false-positive rate on document injection shows containment by blocking has a utility price until content is cleaned.

## Takeaways for tuning a memory stack
- Direct support for B25: a proposal card or memory item that says "approved" must never be the authority; the reviewing LLM was fooled 100 % of the time and only the external policy check held.
- For Engram, served memory should carry no field that any consumer treats as authorization; authority is issued by the harness per task.

## Open questions
- Does containment hold with plausible, non-explicit forged approvals?
