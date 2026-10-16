---
schema_version: 1
artifact_id: N-SURVEY-20261003-02
artifact_type: note
producer: triage
run_id: survey-20261003T054505Z-3590
created_at: 2026-10-03T06:00:00Z
idempotency_key: note:survey:arxiv:2608.18448
input_refs: []
pillar_primary: R3
pillar_secondary: [R10]
memory_stage: retrieval
beliefs_affected:
  supports: []
  contradicts: [B8]
evidence: {directness: medium, control: high, independence: medium, reproducibility: low, applicability: low}
source_url: https://arxiv.org/abs/2608.18448
found_via: survey
---

# More Context, Same Budget: Dual-Bounded Relational Recall Beyond Top-K Retrieval (DBRR)

- **URL:** https://arxiv.org/abs/2608.18448 (HTML v1 read; local copy out/log/raw/2608.18448.html)
- **Type:** paper
- **Author / org:** Thomson D. Nguy, Radiant Institute for Manifold Studies (single author); method tied to US Patent Application 19/362,426
- **Date:** 2026-08-19
- **Retrieved:** 2026-10-03
- **Cited by evidence:** survey run, B8 / H2
- **Relevance to a memory stack:** medium. A matched-ceiling test of "spend part of the budget on graph neighbours of the seeds" versus "spend it on more ranked items", with random-neighbour and shuffled-graph controls.

## TL;DR
- Same BM25 first stage, same maximum object and token ceilings; DBRR splits the budget between seeds and graph-adjacent items, flat baseline takes more ranked items.
- HotpotQA FullWiki dev, n=7,405: complete supporting-fact recovery 58.3% vs 34.5%, paired risk difference 0.237677 [0.226874, 0.248886]; 1,952 improve / 5,261 tie / 192 harm.
- Real graph beats random neighbours (+0.165) and a degree-preserving shuffled graph (+0.309): the gain comes from the link semantics, not from extra items.
- Comparison questions: 0.041695 [0.020175, 0.062542], inconclusive after adjustment; bridge questions carry the gain (0.286921).
- Ceilings matched, realised tokens not reported; split, hop depth and code withheld.

## What it claims / describes
Graph: Wikipedia link graph, 5,233,329 nodes and 19,300,783 edges. Graph-adjacent item is admitted "through a recorded relationship to a selected seed". Budget enforced only as a ceiling: "does not imply identical realized use or equal end-to-end cost". Endpoint is retrieval only (exact recovery of the official supporting-fact set); no LLM, no answer accuracy.

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Complete support recovery | 58.3% (4,315) | flat top-k 34.5% (2,555) | HotpotQA FullWiki dev, n=7,405 | ceilings matched, realised tokens unknown |
| Paired RD, primary | 0.237677 [0.226874, 0.248886] | | Holm [0.224173, 0.251047] | 192 harms |
| Bridge / comparison | 0.286921 / 0.041695 (inconclusive) | | n=5,918 / 1,487 | |
| Real vs random neighbour | 0.165132 (2,017/4,595/793) | | full population | stated value does not match its own counts (0.165294) |
| Real vs shuffled graph | 0.308602 (2,286/5,118/1) | | full population | counts give 0.308575 |

## Mechanism details you could implement
- Reserve a fraction of the context budget for items linked to the top seeds; keep hard caps identical to the flat arm.
- Use random-neighbour and shuffled-graph arms as controls to show the links, not the extra items, produce the gain.

## Limitations, caveats, counter-evidence
- Single author, patent-linked, no code, no corpus or index; verification was recomputation from a sealed package.
- Not chat memory and not software; multi-hop Wikipedia where links are curated hyperlinks.
- No realised token count, so "same budget" is a ceiling claim only.

## Takeaways for tuning a memory stack
- Tension with B8: B8 says graph traversal has not shown lift at matched tokens on chat-memory benchmarks. This is lift at matched ceilings on multi-hop document retrieval, with strong controls. It does not overturn B8 on chat memory, but it is a second targeted-graph positive (after Execution Provenance +4.55) and argues that H2 should include a seeds-plus-neighbours arm and the random/shuffled controls.
- Expansion harms some items (192) and does nothing for comparison questions: expansion needs a when-to-expand policy.

## Open questions
- Seed/neighbour split and hop depth; realised tokens per arm.
