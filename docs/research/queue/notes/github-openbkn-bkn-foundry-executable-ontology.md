---
schema_version: 1
artifact_id: N-SURVEY-20260928-21
artifact_type: note
producer: triage
run_id: survey-20260928T144404Z-faac
created_at: 2026-09-28T14:56:44Z
input_refs: []
supersedes: null
idempotency_key: note:survey:github:openbkn-ai/bkn-foundry
claim_cluster: github:openbkn-ai/bkn-foundry
found_via: survey
source_url: https://github.com/openbkn-ai/bkn-foundry
strength: vendor-benchmark (self-reported, no baseline)
pillar_primary: R10
pillar_secondary: ["R8"]
memory_stage: safety
priority: 3
tags: {"mechanism": ["Object-Relationship-Risk-Action model", "Markdown ontology language (BKN Lang)", "risk types linked to action types", "pre-execution check, in-execution policy interception, post-execution audit", "data virtualisation"], "workload": ["enterprise business agents"], "lifecycle_stage": ["gated action"], "cross_cutting": ["kinetic ontology"]}
evidence: {"directness": "low: benchmark numbers are for Q&A accuracy, not for the risk gate", "control": "none: no baseline, n partly unstated", "independence": "low: self-reported by the maintainers", "reproducibility": "medium: open repo (583 stars, 55 forks), multi-licence 'Apache 2.0 + OpenBKN License'; commit not recorded", "applicability": "medium: the open-source reference for 'actions with risk checks inside the ontology'; business domain, not PDLC"}
beliefs_affected: {"supports": ["B25"], "contradicts": [], "would_create": []}
answers_watch_request: null
---

# OpenBKN bkn-foundry: an ontology platform where business rules and actions execute, with risk types gating actions

- **URL:** https://github.com/openbkn-ai/bkn-foundry (org https://github.com/openbkn-ai; SDK repo bkn-sdk)
- **Type:** repo
- **Author / org:** openbkn-ai
- **Date:** last commit not captured; retrieved 2026-09-28
- **Retrieved:** 2026-09-28 (README through a summarising fetch). The X post that surfaced it was not opened.
- **Cited by evidence:** @leecky, https://x.com/leecky/status/2103794404657950969 ("ontology platform where business rules become executable functions")
- **Relevance to a memory stack:** medium. It is the only open-source system found that puts a precondition-and-risk check between an agent and an action inside the ontology.

## TL;DR
- It "transforms ontology-driven business semantics into runtime services: data, logic, actions, security governance, and observability".
- The model is **Object, Relationship, Risk, Action**. Risk Types are linked to Action Types, with checks before execution, policy interception during it, and an audit log after it.
- Definitions are written in BKN Lang, a Markdown-based language that business experts edit in WYSIWYG editors. The Context Loader and Exec Factory execute them.
- VEGA provides "data virtualization, hides differences between underlying multi-source & multi-modal data", so the claim is that data is not copied.
- Agents (Claude Code, GPT, custom agents) reach it through the BKN CLI in bkn-sdk.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| unstructured-data Q&A accuracy | 99.31% | none | 145 HR samples | self-reported; measures Q&A, not the gate |
| average latency | 43.69 s | none | same | |
| average tokens | 21.36K | none | same | |
| F1 Bench overall accuracy | 92.96% | none | n not captured | |
| SQL waste rate | 8.2% | none | F1 Bench | |
| risk-gate precision or false blocks | not stated | | | the part we care about is unmeasured |

## Mechanism details you could implement
- A Risk type attached to an Action type, evaluated in three phases (pre, during, post). Our analogue: before `merge_pr`, check "any linked Requirement with a failing VERIFIES test" and "any active Constraint on a touched DesignElement".
- Ontology definitions as Markdown files under review. This matches our docs-as-code practice and ADR flow (inference).

## Limitations, caveats, counter-evidence
- The numbers have no baseline and do not test the risk and action layer.
- The licence is not plain Apache-2.0.

## Takeaways for tuning a memory stack
- A usable pattern reference for the kinetic half. It is not evidence that the gate works.

## Open questions
- Is any gate precision or recall published elsewhere? Not found.
