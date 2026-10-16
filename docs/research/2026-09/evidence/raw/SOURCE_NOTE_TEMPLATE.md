# Source note template (every file in evidence/sources/ follows this)

Reader: an engineer tuning their own agent MEMORY STACK in another session. They will not open the original. Be detailed and literal; prefer exact numbers, configs, API shapes, prompts, thresholds and code over paraphrase. Never invent: if something is not in the source, write "not stated". Mark your own inferences with "(inference)". No em dashes.

```
# <Title of the source>

- **URL:** <canonical url>
- **Type:** paper | repo | vendor blog | builder writeup | X article | X post | essay | news | job/lab page
- **Author / org:** ...
- **Date:** ...
- **Retrieved:** 2026-09-26 (local copy: <path if downloaded>)
- **Cited by evidence:** <trend name> / <evidence date + handle>  (from the list you were given)
- **Relevance to a memory stack:** high | medium | low, one line why

## TL;DR
3-5 bullets.

## What it claims / describes
Detailed. Architecture, mechanism, data flow, step by step.

## Numbers
Table of every quantitative result: metric | value | baseline | setup/benchmark | caveat.

## Mechanism details you could implement
Concrete: memory types, write/read/consolidate/forget policies, scoring formulas, thresholds, prompts, schemas, API calls, config flags, code snippets (short, quoted from the source).

## Limitations, caveats, counter-evidence
What the source admits, plus obvious gaps (inference, marked).

## Takeaways for tuning a memory stack
Actionable bullets.

## Open questions
```
