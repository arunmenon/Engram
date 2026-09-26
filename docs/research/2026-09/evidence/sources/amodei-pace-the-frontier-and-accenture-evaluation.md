# We Must Pace the Frontier (Dario Amodei) + Partnering with Accenture on embedded evaluation (Anthropic)

- **URL:** https://darioamodei.com/post/we-must-pace-the-frontier ; https://www.anthropic.com/news/accenture-embedded-evaluation
- **Type:** essay + vendor blog
- **Author / org:** Dario Amodei; Anthropic
- **Date:** essay September 2026 (day not stated); Accenture post 2026-09-18
- **Retrieved:** 2026-09-26 (no local copy)
- **Cited by evidence:** RSI as an explicit oversight object / 2026-09-25 AyushSin164510 (thread post: four levels of US-China agreement); also related to 2026-09-25 Benzinga (Anthropic pause framework)
- **Relevance to a memory stack:** low. Policy framing of RSI; no mechanism. Useful only as the "capability checkpoint" pattern.

## TL;DR
- "AI has been advancing drastically faster, driven primarily by AI's growing ability to build the next generation of AI"; this "is starting to happen across the industry, including at Anthropic" and "could outrun our ability to understand and control these systems."
- Proposes pacing, not halting: "We must slow the pace at which we improve the capabilities of AI models. Progress will still seem fast."
- Three steps: embedded evaluators, democratic coordination on common safety standards, global coordination including authoritarian governments.
- US-China ladder: (1) ban dangerous uses like bioweapons, (2) pre-release testing for acute risks, (3) limit the rate of recursive self-improvement (compared to SALT), (4) full pause, deemed unlikely near term.
- Accenture post: embedded evaluators with "access comparable to an employee's"; at least $1B from each organization over five years. No RSI content.

## What it claims / describes
Trigger mechanism: "capability checkpoints": "if models have capability X, then they need to be accompanied by certifications of alignment properties Y and Z." Example X: "the model is capable of escaping or defeating most common sandboxing methods." The essay does not define how the RSI rate would be measured (the trend "watch" question stays open). Accenture/Faculty evaluators will "watch models take shape in training, follow the decisions that govern how those models are built and deployed, and speak directly to employees"; "Independent embedded evaluators do not reduce our accountability, but help to make it more verifiable." Non-exclusive.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Misaligned swarm scenario | "in 6-12 months such a swarm could be capable of taking over the entire internet", "hundreds of billions of dollars in damage" | | hypothetical | scenario, not measurement |
| Accenture investment | at least $1B each over 5 years | | | |
| 800+ fixes, ~1,000x API error reduction, ~4 person-years | reported by Benzinga post | | | not found in the essay text I retrieved; source is some other Anthropic report, not identified |

## Mechanism details you could implement
- Capability-gated certification (if capability X then require property Y) is the only reusable pattern.

## Limitations, caveats, counter-evidence
- No measurable RSI-rate metric or trigger threshold for level 3. Continual learning and memory are not addressed.

## Takeaways for tuning a memory stack
- Minor: gate memory-stack autonomy levels (e.g. may it rewrite its own consolidation rules?) behind explicit checks, in the capability-checkpoint style (inference).

## Open questions
- What metric would a "speed limit" on RSI use?

---
