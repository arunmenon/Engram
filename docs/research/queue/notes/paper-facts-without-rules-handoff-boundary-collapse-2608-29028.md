---
schema_version: 1
artifact_id: N-SURVEY-20260928-07
artifact_type: note
producer: triage
run_id: survey-20260928T055608Z-7419
created_at: 2026-09-28T06:39:00Z
idempotency_key: note:survey:arxiv:2608.29028
input_refs: []
pillar_primary: R7
pillar_secondary: [R8]
beliefs_affected:
  supports: [B22]
  contradicts: []
evidence:
  directness: high (measures loss of use-scope metadata across a handoff, and leakage downstream)
  control: medium-high (36 scenarios x 4 surfaces x 5 conditions, no-handoff control, gold vs corrupted typed allowlist; Fisher's exact tests)
  independence: medium-high (academic; judge GPT-5.5 Thinking differs from systems under test; external annotators on one experiment)
  reproducibility: high (scenarios, detector, judge harness, labels, scripts at github.com/CrowdDynamicsLab/facts_without_rules_emnlp_2026)
  applicability: medium (privacy/audience boundaries in office-style scenarios, not code; the scope-metadata problem is the same as Engram's scoped briefing)
source_url: https://arxiv.org/abs/2608.29028
found_via: survey
---

# Facts Without Rules: Boundary Metadata Collapse in Multi-Agent LLM Handoffs

- **URL:** https://arxiv.org/abs/2608.29028 (HTML read at https://arxiv.org/html/2608.29028); code https://github.com/CrowdDynamicsLab/facts_without_rules_emnlp_2026
- **Type:** paper (EMNLP 2026 per repo name)
- **Author / org:** Yian Wang, Agam Goyal, Eshwar Chandrasekharan, Hari Sundaram
- **Date:** 2026-08-29
- **Retrieved:** 2026-09-28 (local copy: out/log/h-2608.29028.html)
- **Cited by evidence:** top-down survey, R7 question 3; also P0 "no permission transfer through a snapshot"
- **Relevance to a memory stack:** high, shows scope metadata dies in summaries while facts survive, and that only a correct, typed, machine-readable scope field stops downstream leakage

## TL;DR
- Handoff summaries keep operational facts (survival 0.97 to 0.99) but drop boundary markers (audience limits, disclosure caveats, hedges, ownership); boundary and fact survival are nearly uncorrelated (Pearson r near zero).
- A 25-word budget drops boundary survival sigma_b from 0.954 to 0.690 (GPT-5-mini), 0.880 to 0.580 (DeepSeek-R1-32B), 0.915 to 0.557 (Qwen3-32B).
- Leakage depends on explicitness: vague hedges leak in 35/48 (GPT) and 24/48 (DeepSeek) exact-match; explicit constraints 2/48.
- A typed JSON handoff with a gold `allowed_audiences` field per fact: 0/48 leaks (GPT, DeepSeek), 4/48 (Qwen). Flip the field (corrupted allowlist): 44/48, 38/48, 35/48, back to the no-marker baseline.
- Even without any handoff, a single agent with full markers leaks 20/48 (GPT) and 11/48 (DeepSeek); prompting alone leaks 58/288 and 42/288.

## What it claims / describes
BOUND-Handoff testbed: 36 scenarios across 7 domains, 4 handoff surfaces (free text, compressed free text, preserve-markers instruction, sectioned template, structured schema among the conditions), 5 conditions, 720 design cells. sigma_b is the mean rubric score per upstream marker (preserved 1.0, paraphrased 0.75, weakened 0.35, absent 0.0). Judge GPT-5.5 Thinking, kappa 0.74 and 92 % accuracy on 100 human-labelled items.

## Numbers
| Model | Condition | sigma_b | fact survival |
|---|---|---|---|
| GPT-5-mini | baseline | 0.954 | 0.994 |
| GPT-5-mini | 25-word | 0.690 | 0.997 |
| DeepSeek-R1-32B | baseline | 0.880 | 0.980 |
| DeepSeek-R1-32B | 25-word | 0.580 | 0.972 |
| Qwen3-32B | baseline | 0.915 | 0.986 |
| Qwen3-32B | 25-word | 0.557 | 0.977 |

Marker strength (leaks out of 48, GPT exact / DeepSeek exact): none 44 / 38; vague hedge 35 / 24; soft suggestion 6 / 5; constraint 2 / 2; imperative 2 / 2.
Enforcement: prompt-only 58/288 and 42/288; exact-string redaction 0/288 (semantic leakage remains); gold typed allowlist 0/48; 5 % label error 2/48 and 3/48; 30 % label error 11/48 and 15/48.
Text vs table: the abstract gives sigma_b about 0.80 for "uncompressed free-text handoffs" and about 0.57 at 25 words; Table 2's baseline rows are 0.880 to 0.954. The abstract appears to refer to the free-text surface only while the table baseline pools surfaces (inference); not fully reconciled.

## Mechanism details you could implement
- Carry scope as a typed per-item field (`allowed_audiences` or equivalent scope id) in every served briefing, not as prose. Enforcement degrades gracefully with 5 % label error and fails when the field is wrong.
- Test fixtures: flip the scope field and confirm leakage appears; a check that passes on both the gold and corrupted field is not testing enforcement.

## Limitations, caveats, counter-evidence
- Synthetic, hand-authored English scenarios; downstream agents are LLMs; independent annotation covers one experiment.
- Leakage here is disclosure to the wrong audience, not permission to act.

## Takeaways for tuning a memory stack
- Supports B22's "one scoped interface": scope must be structural and machine-readable at the interface; prose scope in a summary is lost at 25 words and leaks when vague.
- For P0 step 5 (swap adapters, verify scope), add a corrupted-scope fixture.

## Open questions
- Does a harness-side filter on the typed field (rather than the downstream LLM reading it) reach 0 leaks with 30 % label error?
