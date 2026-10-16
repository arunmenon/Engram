---
schema_version: 1
artifact_id: N-SURVEY-20260928-06
artifact_type: note
producer: triage
run_id: survey-20260928T055608Z-7419
created_at: 2026-09-28T06:36:00Z
idempotency_key: note:survey:arxiv:2608.24569
input_refs: []
pillar_primary: R7
pillar_secondary: [R8]
beliefs_affected:
  supports: [B25]
  contradicts: []
evidence:
  directness: high (varies only the handoff transformation, conditions on correct upstream identification, and measures whether the executor acts against a blocker)
  control: high (1,296 primary episodes, direct-handoff controls at 0 % forbidden action, component restoration and leave-one-field-out arms, 13 model variants incl. validation)
  independence: medium (academic; five-model judge panel, overlap with executors not stated)
  reproducibility: low (no code or data URL)
  applicability: medium-high (summaries, plans, tickets, memories and handoff notes are Engram's served artifacts; tasks are synthetic enterprise tasks)
source_url: https://arxiv.org/abs/2608.24569
found_via: survey
---

# When "Must" Becomes "Maybe": Constraint Weakening in LLM Agent Workflows

- **URL:** https://arxiv.org/abs/2608.24569 (HTML read at https://arxiv.org/html/2608.24569)
- **Type:** paper
- **Author / org:** Yiheng Sun, Huifei Wang, Yancheng Zhu, Zhenyu Li, Zebin Zhao, Yifan Yuan
- **Date:** 2026-08-25
- **Retrieved:** 2026-09-28 (local copy: out/log/h-2608.24569.html)
- **Cited by evidence:** top-down survey, R7 question 3 (handoff contracts)
- **Relevance to a memory stack:** high, it names the minimum fields a summary or briefing must carry so a binding constraint stays binding, with a clean restoration experiment

## TL;DR
- A blocker is represented as z = (s, q, o, f): stop status, unresolved prerequisite, responsible authority, admissible fallback.
- Handoff compression turns binding state into caveats: normal compression gives 100.0 % deactivation and 54.2 % forbidden action; direct state gives 0.0 % and 0.0 %.
- Restoring all four fields restores 100.0 % preservation and 0.0 % forbidden action (n = 64); any single field alone does not (status only: 26.6 % preserved, 0.0 % unsafe; prerequisite only: 10.9 % preserved, 73.4 % unsafe).
- Omitting stop status drops blocker recognition from 99.2 % to 40.6 % and reintroduces 7.0 % forbidden action.
- Endpoint controls (hard authorization, permission check, human approval) cut forbidden action to 0.0 % even when the artifact is broken.

## What it claims / describes
"Topical retention is insufficient": an artifact may mention an unresolved condition while turning it from a requirement into information. The study fixes the blocker before the transformation, varies only the transformation (compression, plan assimilation, convergence, ownership deferral, precedent substitution), and gives the executor only the resulting artifact. This extends Governance Decay / ConstraintRot (arXiv 2606.22528, already in the September landscape) by decomposing which fields carry the binding force and by comparing artifact repair with endpoint controls.

## Numbers
Main matrix (P = preserved, D = deactivated, Unsafe = forbidden action, %):
| Condition | n | P | D | Unsafe |
|---|---|---|---|---|
| P0 direct | 120 | 100.0 | 0.0 | 0.0 |
| P4 ownership deferral | 120 | 23.3 | 76.7 | 60.8 |
| S3 multihop summary | 72 | 2.8 | 97.2 | 31.9 |
| S4 schema summary | 72 | 72.2 | 27.8 | 0.0 |
| C4 plan assimilation | 72 | 33.3 | 65.3 | 29.2 |
| E4 low-risk frame | 72 | 23.6 | 76.4 | 33.3 |

Compression gradient (n = 48 each): direct 0 / 0; light summary D 25.0, unsafe 0.0; normal handoff D 100.0, unsafe 54.2; compressed D 100.0, unsafe 83.3; aggressive multihop D 100.0, unsafe 79.2.
Component restoration (n = 64 each, unsafe %): no repair 81.2; status only 0.0; prerequisite only 73.4; authority only 21.9; fallback only 10.9; all four 0.0 (P 100.0).
Fixed-artifact interventions (n = 128 each, unsafe %): artifact no repair 85.2; all four 0.0; endpoint plain 85.2; soft auth 1.6; hard auth 0.0; permission 0.0; human approval 0.0.
Cost: primary panel 1,296 episodes, 6,416 API calls, 23.1M tokens; validation 476 episodes, 6.6M tokens. Model heterogeneity: DS-V4-Pro thinking 58.3 % unsafe vs GPT-5.4-mini 0.0 % in one table (Table 19 as extracted).

## Mechanism details you could implement
- Any summary, briefing or handoff that contains a constraint should carry it as a typed record with four fields: `stop_status`, `unresolved_prerequisite`, `responsible_authority`, `admissible_fallback`. Mark these as non-compressible.
- Pair artifact repair with an endpoint check outside the model: endpoint controls reached 0.0 % unsafe even when the artifact had lost the blocker.

## Limitations, caveats, counter-evidence
- Synthetic enterprise tasks with pre-identified valid blockers; production prevalence out of scope.
- Authority field labelling is less reliable (65.25 % agreement, macro F1 0.636) than overall labelling (94.83 %, kappa 0.887).
- Under 15 to 20 % label flips the unsafe-action contrast becomes inconclusive.
- The four-field representation is the authors' operationalisation, not a proven minimum for other constraint classes.

## Takeaways for tuning a memory stack
- Engram's Consumer 4 summaries and any H3 curated briefing are handoff artifacts; test whether they keep all four fields, not whether they "mention" the constraint.
- Supports B25 from the other side: endpoint authority (hard auth, permission, human approval) contained every broken artifact.

## Open questions
- Does the result hold for PDLC constraints (for example "do not merge until security review") on real repositories?
