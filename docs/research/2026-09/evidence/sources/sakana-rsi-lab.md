# Sakana AI RSI Lab (announcement, Schmidhuber advisor post, MTS job page)

- **URL:** https://sakana.ai/rsi-lab/ ; https://sakana.ai/schmidhuber/ ; https://sakana.ai/careers/member-of-technical-staff-rsi-lab/
- **Type:** job/lab page (three pages combined)
- **Author / org:** Sakana AI
- **Date:** Schmidhuber post 2026-09-24; RSI Lab page date not stated (post says "announced ... earlier this year"); job page not dated
- **Retrieved:** 2026-09-26 (no local copy)
- **Cited by evidence:** Frozen-model self-improvement through harness and skills / 2026-09-25 SakanaAILabs
- **Relevance to a memory stack:** low to medium. Roadmap and hiring, no mechanism. The useful part is the lab's own admitted failure modes and the archive-of-variants idea from the Darwin Gödel Machine.

## TL;DR
- Unifies prior work (LLM², Darwin Gödel Machine, ShinkaEvolve, ALE-Agent, Digital Red Queen, The AI Scientist) into one RSI mission: "open-ended, adaptive architectures that collectively self-improve".
- Stresses sample efficiency under constraint: "extract structured lessons from its own failures, not by burning more inference".
- Admitted failure modes: "evolutionary loops that drift off-distribution, self-modifications that pass benchmarks but fail in deployment".
- Jürgen Schmidhuber joins as Chief Scientific Advisor; focus on world models and physical AI.

## What it claims / describes
Four-phase trajectory: (1) Agent-Native Models, (2) The AI Scientist, (3) Recursive Self-Improvement ("agents autonomously upgrading foundation architectures"), (4) Democratized AI ("exponential self-improvement becomes a public good rather than winner-take-all"). Philosophy: "progress through ideas, not just compute". Commitment to "publish openly, including negative results, and design our self-improvement loops with verifiable safeguards". "Responsible RSI is not a constraint on capability; it is what makes capability sustainable."

Schmidhuber post: RSI Lab to build systems that research, rewrite their own code, and act in physical environments via "Agent-Native World Models"; cites his 1987 thesis on meta-learning and the Gödel Machine. Quote: "The future of intelligence is not just language; it is physical AI powered by World Models."

Job page (Member of Technical Staff, Tokyo; full-time, visiting, internship): "Discover fundamental new laws of machine intelligence that bend the scaling curve", "Build world models that serve as verifiable simulators for agentic reasoning", evolutionary dynamics in domains like cybersecurity, and "systems infrastructure for the RSI loop". No safety evaluation framework mentioned.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Darwin Gödel Machine SWE-bench | "more than doubled" baseline, +30 pts absolute | own baseline | 2025 | lab summary, not re-verified |
| ShinkaEvolve | solved optimization problems with 150 samples | not stated | 2025 | |
| ALE-Agent | 1st of 804 humans, AtCoder Heuristic Contest | | 2025 | |
| The AI Scientist | published in Nature 2026-03-26 | | | |

## Mechanism details you could implement
- Only one: Darwin Gödel Machine keeps "an evolving lineage of agent variants" (archive of versions rather than a single current best). No other mechanism detail on these pages.

## Limitations, caveats, counter-evidence
- Recruiting and positioning material. No new results. Safety language is aspirational; no concrete safeguard described.

## Takeaways for tuning a memory stack
- Keep a lineage/archive of memory configurations, not only the latest (matches EvoSkill frontier and RRSI ledger).
- Take their two named failure modes as test cases: off-distribution drift and "pass benchmarks but fail in deployment". Evaluate memory changes on held-out, deployment-like tasks.

## Open questions
- Will the lab publish the promised negative results and safeguards?

---
