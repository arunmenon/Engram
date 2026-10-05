---
schema_version: 1
artifact_id: N-20260930-09
artifact_type: note
producer: triage
run_id: triage-20260930T014506Z-8351
created_at: 2026-09-30T01:57:27Z
input_refs: [{"artifact_id": "post:2104865418573693324", "file_id": null, "sha256": null}, {"artifact_id": "post:2105044238518165770", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.35576
claim_cluster: arxiv:2609.35576
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.35576
source_commit: github.com/psidharth567/Share-Borne-Virus 6e98e866d02aa30066a250c30c992aae06bb43d1 (HEAD 2026-09-29, not cloned)
strength: paper-single-benchmark
pillar_primary: R8
pillar_secondary: ["R2", "R7"]
tags: {"mechanism": ["artifact-mediated memory poisoning", "persistent MEMORY.md", "attacker endpoint reinjection", "injection classifier on memory writes"], "workload": ["multi-agent human-mediated document workflows"], "lifecycle_stage": ["safety", "write_gate"], "cross_cutting": ["shared_state"]}
memory_stage: safety
evidence_grade: {"directness": "high: measures infection and hop survival in simulated workflows with named models", "control": "medium: per-model comparison and a prompt-only variant; defence measured only as a detection count; synthetic networks", "independence": "medium: academic group (includes Mario Fritz); no vendor stake", "reproducibility": "medium: repo at a known HEAD, but only the GPT-OSS-120B attack template released", "applicability": "high: our agents share documents and write persistent memory; the propagation path is shared artifacts, not agent-to-agent messages"}
beliefs_affected: {"supports": ["B24", "B25"], "contradicts": [], "would_create": ["A prompt-injection classifier on memory writes catches instruction-bearing memories but not planted false beliefs without instructions (4 false positives on 24 benign instruction-like memories); a write gate needs a provenance or belief check, not only an injection check"]}
claim_correction: none
---

# Share-Borne AI Virus: Memory-Hopping Attacks Across LLM Agents (arXiv 2609.35576)

- **URL:** https://arxiv.org/abs/2609.35576 (HTML read: https://arxiv.org/html/2609.35576v1)
- **Type:** paper (37 pages)
- **Author / org:** Sidharth Pulipaka, Ansh Sharma, Stanislau Hlebik, Leonidas Raghav, Vyas Raina, Ivaxi Sheth, Mario Fritz. Code: https://github.com/psidharth567/Share-Borne-Virus
- **Date:** submitted 2026-09-28
- **Retrieved:** 2026-09-30. Repo HEAD `6e98e866d02aa30066a250c30c992aae06bb43d1` (2026-09-29) via the GitHub API, not cloned.
- **Cited by evidence:** memory feed 2026-09-29, @KostyaAI (https://x.com/KostyaAI/status/2104865418573693324); reply @0xVeyyy (https://x.com/0xVeyyy/status/2105044238518165770, a product plug for "Atomic Memory Cloud", no evidence).
- **Relevance to a memory stack:** high. Shows poisoned content stored in one agent's persistent memory being reproduced into new artifacts and infecting other agents over many hops, and measures one write-gate defence.

## TL;DR
- Threat: a poisoned shared artifact infects an assistant's persistent memory (hop 1); the assistant later reproduces the adversarial state into a new artifact, which infects other assistants, with no direct agent-to-agent channel.
- Setup: OpenClaw harness with a persistent MEMORY.md; 36 synthetic human-agent workflows (3 to 12 agents, 10 to 20 steps, mean 14.3) plus three large universes (30 agents, 60 steps).
- Endpoint-assisted infection of agents: GPT-5.6 Luna 38%, Kimi-K2.6 47%, GPT-OSS-120B 85%, DeepSeek-V4-Pro 98%; large universes reach "90-100% of agents" with chains to hop 8 for the two open models.
- Prompt-only (no attacker endpoint), DeepSeek-V4-Flash: 21% fully infected, per-hop continuation 0.73.
- Defence tested: an injection classifier screening memory writes detected instruction-bearing memories "with high reliability", with 4 false positives on 24 benign instruction-like memories; "False beliefs without instructions evade it."

## What it claims / describes
Attack prompt instructs an agent to (1) store the adversarial goal in persistent memory after reading an infected artifact, (2) retrieve and reproduce that state in later documents, and (3) route artifacts through an attacker-controlled endpoint that reinjects the full payload. The prompt-only variant drops step 3.

## Numbers
Endpoint-assisted propagation.

| model | agents infected | artifacts infected | hop 2 survival | hop 4 survival | per-hop continuation p |
|---|---|---|---|---|---|
| GPT-5.6 Luna | 38% | 33% | 57% | 24% | 0.71 |
| Kimi-K2.6 | 47% | 50% | 67% | 44% | 0.84 |
| GPT-OSS-120B | 85% | 83% | 92% | 61% | 0.93 |
| DeepSeek-V4-Pro | 98% | 97% | 93% | 76% | 0.98 |

| metric | value | setup | caveat |
|---|---|---|---|
| prompt-only, DeepSeek-V4-Flash | 21% fully infected; hop 2 30%, hop 3 12%; p = 0.73 | no endpoint | "lower bounds at modest search budget" |
| memory-write injection classifier | high detection of instruction-bearing memories; 4 FP / 24 benign instruction-like | defence eval | false beliefs without instructions evade it; detection rate not captured as a number |
| Grok 4.6 attack search | halted at about 0.2 success | cost constraint | |

## Mechanism details you could implement
- Test harness idea: seed one shared document, run a multi-agent workflow with persistent memory, and measure agents infected, artifacts infected and per-hop survival.
- Mitigations the paper discusses but does not test: outbound-host allowlists, user confirmation before upload to new services, prioritising widely shared artifacts for screening.
- Pair an injection screen on memory writes with a provenance rule: a memory derived from a shared artifact carries the artifact id so a later revocation can find every descendant (inference, consistent with synthesis section 4b).

## Limitations, caveats, counter-evidence
- Endpoint mechanism needs outbound network access; strict egress stops it.
- Synthetic network structures; real collaboration graphs may differ.
- Templates for deployed models withheld except GPT-OSS-120B ("available to researchers upon specific request").
- Stronger frontier models were more resistant (Luna 38%), and attack search on them was costly.

## Takeaways for tuning a memory stack
- Treat any memory written after reading a shared artifact as derived from that artifact, and keep the link; this is what makes a later purge possible.
- An injection classifier on writes is necessary but not sufficient: planted false facts pass it. A contradiction or source check against trusted memory is the missing half (inference).
- Egress control on the agent runtime blocks the strongest variant.

## Open questions
- Detection rate of the write-time classifier as a number, and its model.
- Does provenance-scoped retrieval (only serve memories whose source artifact is trusted) cut hop survival? Not tested.

## Grading and labels
- Directness high; control medium; independence medium; reproducibility medium; applicability high.
- Pillars: R8 primary (poisoned evidence, execution authority), R2 (write gate), R7 (multi-agent exchange through shared artifacts). Memory stage: safety. Tags shared_state.
- Beliefs: supports B24 (extracted memories are untrusted input) and B25 (evidence cannot authorise its own use: the attack works by making stored content act as instruction). Would create the write-gate insufficiency belief in frontmatter.
- Contradiction rows: none. Related bus items: `paper-backchain-memory-attacks-2609-32186.md` (card PC-20260929-06), PMPA persistent memory poisoning, MemSecBench.

## Origin chain
@KostyaAI post (2104865418573693324) -> arXiv 2609.35576 abstract and HTML v1 -> threat model, experimental setup, propagation table, prompt-only variant, defences and limitations -> this note. Independence: academic authors; models from four vendors; no shared authors with other notes in this run.
