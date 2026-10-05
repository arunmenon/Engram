---
schema_version: 1
artifact_id: N-SURVEY-20260928-05
artifact_type: note
producer: triage
run_id: survey-20260928T055608Z-7419
created_at: 2026-09-28T06:32:00Z
idempotency_key: note:survey:arxiv:2605.11039
input_refs: []
pillar_primary: R8
pillar_secondary: [R7]
beliefs_affected:
  supports: [B25]
  contradicts: []
evidence:
  directness: medium-high (enforces that untrusted content may not determine authority-bearing tool arguments; memory is one such source)
  control: high (AgentDojo, five models, compared against NoDefense, FIDES, CaMeL; ablations of roles and cross-step provenance)
  independence: medium (academic; authors' own method compared to baselines)
  reproducibility: low-medium (code URL not found in the HTML read; AgentDojo is public)
  applicability: medium (tool-using agents on AgentDojo; engineering agents' authority-bearing args are commands, targets, credentials)
source_url: https://arxiv.org/abs/2605.11039
found_via: survey
---

# The Granularity Mismatch in Agent Security: Argument-Level Provenance Solves Enforcement and Isolates the LLM Reasoning Bottleneck (PACT)

- **URL:** https://arxiv.org/abs/2605.11039 (HTML read at https://arxiv.org/html/2605.11039)
- **Type:** paper
- **Author / org:** not captured in the fields read
- **Date:** May 2026 (v1)
- **Retrieved:** 2026-09-28 (local copy: out/log/h-2605.11039.html)
- **Cited by evidence:** top-down survey, R8 question 3 (B25)
- **Relevance to a memory stack:** medium-high, gives a concrete, measured rule for "evidence cannot authorise its own use": untrusted-origin values may fill content fields but not authority-bearing fields

## TL;DR
- Injection becomes dangerous "not when untrusted content appears in context, but when it determines an authority-bearing argument".
- PACT tags each runtime value with origin, trust level (TRUSTED > USER > TOOL_OUTPUT > EXTERNAL) and obligations, assigns each tool argument a semantic role (target, command, credential, content, selector, control), and checks the origin against a per-role trust contract.
- On AgentDojo, PACT and CaMeL both reach 100.0 % security on all five models tested; PACT keeps 8 to 16 pp more utility than CaMeL on the three strongest (38.1 to 46.4 % vs 28.9 to 30.9 %).
- Both still lose utility relative to no defense (e.g. GPT-4o-mini 59.8 % none, 46.4 % PACT, 30.9 % CaMeL).
- Runtime check cost is negligible (P99 under 272 microseconds); the bottleneck is inferring roles (87.1 % accurate) and provenance (77.4 %) automatically on 20 real MCP tools.

## What it claims / describes
Contract hierarchy L0 whole-call boundary, L1 per capability, L2 per argument role, L3 L2 plus scoped discharge certificates from trusted procedures. Deployment provenance inference: exact structural matching, role-aware heuristics, then an LLM classifier for ambiguous arguments, with fallback to the more conservative label on low confidence or authority-bearing cases.

## Numbers
AgentDojo (utility / security, %), verified against the HTML table:
| Model | NoDefense | FIDES | CaMeL | PACT |
|---|---|---|---|---|
| Qwen-turbo | 20.6 / 92.6 | 19.6 / 88.9 | 11.3 / 100.0 | 18.6 / 100.0 |
| Qwen-plus | 60.8 / 88.9 | 59.8 / 85.2 | 29.9 / 100.0 | 45.4 / 100.0 |
| Qwen-max | 46.4 / 96.3 | 50.5 / 96.3 | 29.9 / 100.0 | 38.1 / 100.0 |
| Qwen2.5-72B | 46.4 / 96.3 | 48.5 / 96.3 | 28.9 / 100.0 | 42.3 / 100.0 |
| GPT-4o-mini | 59.8 / 88.9 | 55.7 / 88.9 | 30.9 / 100.0 | 46.4 / 100.0 |

Mixed-trust diagnostic suite (n = 17 scenarios): Vanilla 100 / 0 security, 8 false negatives; FIDES 66.7 / 37.5; CaMeL 33.3 / 100, 6 false positives; PACT L2 (oracle provenance) 100 / 100, 0 FP, 0 FN.
Ablation: no roles (L1) 40.0 / 100.0; no cross-step provenance 100.0 / 80.0.
Text vs table: the abstract says "100% security on the three strongest models"; the table shows 100.0 % on all five. The utility range quoted (38.1 to 46.4 %) corresponds to Qwen-max, Qwen2.5-72B and GPT-4o-mini. Not a contradiction, but the text understates the table.

## Mechanism details you could implement
- Classify every field an agent may act on as authority-bearing (target, command, credential, control) or not (content, selector); values whose provenance includes memory or retrieved content may fill content fields only, unless a trusted procedure discharges them.
- Propagate provenance across replanning steps; the ablation shows dropping cross-step tracking cuts security to 80 %.

## Limitations, caveats, counter-evidence
- Security baselines are already 88.9 to 96.3 % without defense on these models, so headroom is small.
- Content-channel attacks (harmful text in permitted content fields) and tool-selection attacks are out of scope.
- Deployment depends on role and provenance inference at 87.1 % and 77.4 %.

## Takeaways for tuning a memory stack
- Supports B25 with a mechanism that costs less utility than CaMeL: memory may inform, not choose destinations or commands.
- For Engram, the served briefing should expose provenance per item (P5 `source_class`) so a harness can apply argument-level contracts downstream.

## Open questions
- Utility cost on build-time engineering tasks, where commands are often legitimately derived from memory (for example a remembered build command).
