# LintPal: Markdown rules checked against Git diffs with Jev Noul decisions and a deterministic severity gate

- **URL:** https://github.com/diffpal/lintpal
- **Type:** repo
- **Author / org:** diffpal, MIT license (npm package `lintpal`; README quickstart pins `lintpal-version: "0.4.1"`)
- **Date:** commit read `905df34af9edd6676d3c8f3d236cde116d8acd4e` (2026-09-25)
- **Retrieved:** 2026-09-26 (local copy: /private/tmp/claude-501/-Users-arunmenon-projects-localai-signals/3f9824a6-23ac-471e-adc7-a1ca0ec806fd/scratchpad/repos/lintpal, shallow clone)
- **Cited by evidence:** Typed-decision tier displacing LLM calls on bounded classification / 2026-09-25 metalagman
- **Relevance to a memory stack:** low. Not a memory system. Useful only as a clean reference client for the Jev System One API (typed request/response validation, retries, batching limits, per-rule thresholds).

## TL;DR
- Each Markdown file under `.lintpal/rules/` is one rule; its body becomes the `instructions` of a Jev question, evaluated against bounded committed diff context.
- A finding fires when the Noul "true" probability `>=` the rule threshold (default 0.95; frontmatter `threshold:`). Severity and message come from the rule, never from the model.
- Default provider is Jev (`LINTPAL_PROVIDER=jev`, `LINTPAL_MODEL=jev-latest`, `TYPESAFE_API_KEY`); OpenRouter and a trusted custom System One endpoint are alternatives.
- The only in-repo quality evaluation is an 8-case offline corpus with *fake* Noul probabilities (3 TP, 3 TN, 1 FP, 1 FN), which the docs say is "not measured model precision".

## What it claims / describes
"Turn plain-English engineering rules into pull-request checks." Pipeline (README): Rules (load `.lintpal/rules/**/*.md`) -> Diff (changed lines between two committed revisions) -> Decisions (each applicable rule through the provider) -> Findings (line-anchored, findings v5 JSON schema) -> Feedback (GitHub review summary plus inline comments, severity gate). "LintPal is a focused policy checker. It does not generate a narrative code review or invent new review criteria during a run." docs/architecture.md: "The model cannot supply finding text or an anchor."

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Default rule threshold | 0.95 | n/a | docs/rule-authoring.md | "a decision setting, not measured model accuracy" |
| Offline eval corpus | 8 cases: 3 TP, 3 TN, 1 FP, 1 FN | n/a | `internal/apps/lintpal/eval/testdata` | fake Noul probabilities; tests code paths only |
| Live accuracy / cost vs LLM | not stated | | `scripts/eval-live.sh` exists, no results committed | |
| Transport limits | 1 MiB request, 2 MiB response, 3 attempts, 15 s per attempt, backoff 100 ms doubling capped at 2 s | | provider/systemone/transport.go | retries on network error, 429, 529, 5xx only |
| Batch planning | 128 questions per batch default (hard 1024); request 24,000 bytes default (hard 30,000, "below the portable 32K context target"); state 20,000 bytes default (hard 28,000) | | contextplan/contracts.go | |
| Default gate exit code | 10 when a high or critical finding blocks | | README | |

## Mechanism details you could implement
- Rule frontmatter accepts only `severity` (low/medium/high/critical, default medium), `threshold` (0 to 1, default 0.95) and `title`; unknown or duplicate fields are rejected. `--rule-threshold` / `LINTPAL_RULE_THRESHOLD` override all rules.
- Typed question primitives in internal/apps/lintpal/jev/provider.go: `NoulQuestion{Instructions, Criteria *{True, False}}`, `ChoiceQuestion{Instructions, Criteria map[string]string}`, `ScoreQuestion{Instructions, Criteria []string}`. Answers: `NoulAnswer{Probability}`, `ChoiceAnswer{Choice, Probabilities, Confidence}`, `ScoreAnswer{Score, Legend, Probabilities, Confidence}`. Wire shapes are recorded in the Jev API note (docs-typesafe-jev-api.md).
- Request validation (jev/validate.go): model non-empty, at least one question, state must JSON-encode to a string, object or array; question id non-empty and at most 128 chars; choice needs 2 to 255 options; score needs 2 to 10 levels. Response validation: exactly one answer per question; Noul probability in [0,1]; choice probabilities form a distribution over the declared options and the chosen option has the max probability (1e-6 tolerance); score in [0, levels-1], probabilities sum to 1 within 1e-6, and `score` within 0.02 of the probability-weighted mean; `usage.input_tokens` and `usage.output_tokens` required.
- Decision rule: "A rule triggers when the Noul true probability reaches its threshold; equality triggers."

## Limitations, caveats, counter-evidence
- No live precision/recall or cost comparison against an LLM reviewer is published in the repo, so it gives no direct evidence for the "displacing LLM calls" trend beyond architecture (inference).
- The live eval helper refuses the `jev-latest` alias and requires an exact model id, implying the alias can move between runs.

## Takeaways for tuning a memory stack
- The pattern "model returns only a probability, the application owns all text, anchors and severity" transfers directly to memory write gates: let the decision model say whether to store, and never let it author the stored content unless a separate step does.
- Per-item thresholds in config (like per-rule `threshold`) are a simple way to run different precision targets for different memory types (inference).
- Validate decision-model responses strictly (distribution sums, one answer per question) before acting.

## Open questions
- Live precision of Jev on these rules, and cost per PR versus an LLM reviewer: not stated.

---
