---
schema_version: 1
artifact_id: N-20260928-21
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:07:08Z
input_refs: [{"artifact_id": "post:2104537487804678214", "file_id": null, "sha256": null}, {"artifact_id": "post:2104541252868022382", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:cloudgeni-ai/genigrep
claim_cluster: github:cloudgeni-ai/genigrep
feeds: ["decision"]
primary_source: https://github.com/Cloudgeni-ai/genigrep
source_commit: da10c5e82845356cebc5b8f918389d0025f08eaf
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R3", "R6"]
memory_stage: reranking
priority: 1
tags: {"mechanism": ["jev-noul-judge", "lexical-recall-then-judge", "lexical-guard", "sufficiency-rating", "one-level-lead-following", "token-budget-pack"], "workload": ["coding-agent", "code-investigation-questions", "typescript-monorepo"], "lifecycle_stage": ["read", "rerank", "assembly"], "cross_cutting": ["tool-wording", "cost", "latency", "privacy-hosted-api", "fail-closed"]}
evidence_grade: {"directness": "high: Jev reranks code passages served to a coding agent on the builders' own monorepo, the same shape as our build-time reads", "control": "medium: paired on/off per question, two blind graders, paired bootstrap CIs, a keyword-only ablation; but only run 1 excludes zero on cost and time", "independence": "low: builders evaluated their own tool on their own repo; grader identity not stated", "reproducibility": "low: question set, grading rubric and per-question results are not published; engine and thresholds are pinned in the repo", "applicability": "medium: code investigation questions only; no effect on 24 bug-fix tasks; one TypeScript repo"}
beliefs_affected: {"supports": ["B11", "B20"], "contradicts": ["B9"], "would_create": ["Presenting a decision-model sufficiency verdict to an agent as a stop signal lowers answer quality; a numeric rating plus an explicit statement of what it cannot see restored parity (OpenGeni, 26 questions)"]}
claim_correction: Post says ~7% cheaper and ~10% faster at same answer quality; source measured this on 26 questions in the OpenGeni harness (not the released CLI/MCP), only run 1 (gpt-6-astra) has CIs excluding zero (-6.6% cost [-11.5, -1.9], -9.1% time [-13.4, -4.6]); run 2 CIs include zero; no effect on bug fixing.
---

# genigrep (Cloudgeni-ai): TypeSafe Jev as a file and passage judge for coding-agent code search

- **URL:** https://github.com/Cloudgeni-ai/genigrep (evaluation methodology: https://github.com/Cloudgeni-ai/opengeni/blob/main/docs/code-search.md)
- **Type:** repo (plus the upstream OpenGeni evaluation doc)
- **Author / org:** Cloudgeni-ai (OpenGeni); Apache-2.0; npm `@opengeni/genigrep` 0.1.1
- **Date:** commit `da10c5e82845356cebc5b8f918389d0025f08eaf`, 2026-09-28 13:25:03 +0200, "Fix the npx MCP command in the README (0.1.1)"
- **Retrieved:** 2026-09-28, shallow clone at repos/genigrep (commit above). Read: README.md, docs/how-it-works.md, NOTICE, src/engine/code-search/config.ts, src/engine/code-search/judge.ts. OpenGeni docs/code-search.md read through one WebFetch of the raw file (summarised by the fetch tool; quotes below are the fetch tool's quotes).
- **Cited by evidence:** https://x.com/bendikdev/status/2104537487804678214 (@bendikdev, 2026-09-28), reply https://x.com/IuliiaPetryshyn/status/2104541252868022382 (@IuliiaPetryshyn, "awesome results!", no content)
- **Relevance to a memory stack:** high. Jev sits exactly at our reranking stage for build-time reads (lexical recall, then Jev judges files and passages, then a budgeted pack and a sufficiency score), measured with a paired, blind-graded agent eval on a real engineering codebase, and with a documented failure (the first version made answers worse).

## TL;DR
- Pipeline: ripgrep keyword recall (up to 240 files, IDF-scored) -> Jev wave 1 file triage (noul per file, select p >= 0.6, up to 16, always the 8 best judged plus the 5 best lexical) -> Jev wave 2 passage relevance (noul per passage, T2 0.5) -> Jev wave 3 one-level lead following (up to 6 definitions, p >= 0.5) -> pack into 12,000 tokens -> one Jev "evidence rating" call. Jev only scores; the agent reasons.
- Measured (OpenGeni harness, 26 real code questions on the OpenGeni TypeScript monorepo, tool on vs off, two blind graders, paired bootstrap): run 1 `gpt-6-astra` cost -6.6% [-11.5, -1.9], time -9.1% [-13.4, -4.6]; run 2 `gpt-6-sol` xhigh cost -7.5% [-14.2, +0.4], time -9.8% [-17.9, +0.6]. "Answer quality was equal." Jev about $0.006 per question.
- Claim correction: the post's "~7% cheaper, ~10% faster, same answer quality" is one repo, 26 questions, one harness, and only run 1 is significant on its own; the released CLI, MCP server, skill and derived keywords "were not part of the evaluation". Bug fixing (12 Terminal-Bench 2.1 + 12 SWE-rebench, one trial): no measurable effect.
- The "15% cheaper but worse answers" first version is confirmed by the OpenGeni doc: packs labelled `sufficient`/`partial` with "search further only for reported gaps" saved 15% but "lost a few answers"; blind re-grading showed the agent stopping at a pack covering only one side. The fix was wording: show the rating as a number and say it "cannot see what the search missed".
- Ablation: keyword-only ranking of the same pipeline "lost 7.7 points of answer quality", so genigrep fails closed (exit 4) instead of falling back.

## What it claims / describes
genigrep is the `code_search` engine of the OpenGeni agent, extracted into a CLI (`ggr`), an MCP server (`ggr mcp`, one read-only tool `code_search`) and a library. NOTICE: the engine in `src/engine` was ported from OpenGeni `packages/jev` at commit `fe7ea0a6cf3f094cd00bbf066a2107fef049fe19`, "with ranking, thresholds and Jev prompts unchanged" (README, Origin). Division of labour (docs/how-it-works.md): code does ripgrep, IDF scoring, windowing, definition following and packing; Jev "answers narrow yes/no questions ... with a probability. It never writes text"; the agent reads the passages and reasons.

Step by step (docs/how-it-works.md, "The pipeline"):
1. **Recall.** Keywords expanded to camelCase, snake_case, kebab-case and spaced variants; one case-insensitive ripgrep pass; files over 4 MB and lines over 8,000 chars skipped; up to 25 matching lines per file per keyword. Score = IDF of distinct matched keywords + path bonus (0.5 x IDF) + 0.1 x log(1 + hits). Tests and changelogs weighted 0.6 unless the question is about them. Top 240 files become candidates.
2. **File triage (Jev wave 1).** Each candidate shown as path plus 3 best matching lines cut to 160 chars, 60 files per request. Select p >= 0.6 (T1), up to 16; "The 8 best-ranked files are always selected, and the 5 best files by keyword score are always kept, so one judge miss cannot drop an obvious candidate."
3. **Passage check (Jev wave 2).** Files cut into windows aligned to the enclosing declaration (up to 40 lines up, 120 down); windows merged or split (max 150 lines); best 5 per file; at most 80 passages, round-robin across files; 4 passages per Jev request. Jev scores relevance and, per sub-question, coverage.
4. **Leads (Jev wave 3).** From the 12 most relevant passages (rel >= 0.5), collect identifiers used but not defined; Jev scores up to 60; follow up to 6 with p >= 0.5, one level only.
5. **Pack and evidence rating.** Order: best passage per sub-question, then every passage with rel >= 0.5, then if fewer than 4 passed the next best above 0.1. Budget 12,000 tokens at 3.2 chars/token. One final Jev request over up to 60,000 chars of packed passages gives the evidence rating.

Jev client (docs/how-it-works.md, "Jev"): splits questions so each request stays within "32k tokens for the state plus the longest question, 64k for the state plus all questions"; up to 16 concurrent requests; keep-alive connections warmed while ripgrep runs; retries network errors, timeouts, 429 and 5xx up to two times; default timeout 10 s. "OpenGeni measured about 0.4 seconds per request." MCP server circuit breaker: after 3 consecutive Jev outages it refuses calls for 5 minutes (30 minutes after 401/402/403).

Evaluation (README "Measured results" and OpenGeni docs/code-search.md via WebFetch): "26 real code questions from staging, answered twice per arm by the OpenGeni agent (gpt-6-astra) on a Connected Machine, with the tool on and off in parallel, graded blind by two graders." README adds a second run with `gpt-6-sol` at xhigh reasoning. The OpenGeni doc also states: "The same engine in a plain Codex CLI harness saved 16% cost and 11% time" (no n or CI given in the fetched text).

## Numbers

| metric | value | baseline | setup with n | caveat |
|---|---|---|---|---|
| agent cost, run 1 | -6.6% [-11.5, -1.9] | same agent, tool off | 26 questions, `gpt-6-astra`, paired, 95% paired bootstrap (README, Measured results table) | OpenGeni doc words it "cost -6.6% (95% CI 2-12%)" |
| agent time, run 1 | -9.1% [-13.4, -4.6] | tool off | same | |
| agent cost, run 2 | -7.5% [-14.2, +0.4] | tool off | 26 questions, `gpt-6-sol`, xhigh reasoning | CI includes zero; README: "agrees with run 1 but does not confirm it on its own" |
| agent time, run 2 | -9.8% [-17.9, +0.6] | tool off | same | CI includes zero |
| model calls per question, run 2 | 19.4 to 16.2 | tool off | same | README table "Other" column |
| pass rate, run 2 | +1.9 points [-4.8, +8.7] | tool off | same | "Answer quality was equal"; rubric not published |
| model requests per question, run 1 | "1.4 fewer" | tool off | OpenGeni doc | |
| Jev cost | "about $0.006 per question" / "per call" | n/a | OpenGeni doc | |
| earlier wording (sufficient/partial labels) | "saved 15%" but "lost a few answers" | tool off | OpenGeni doc | count of lost answers not stated |
| keyword-only ranking ablation | "lost 7.7 points of answer quality" | Jev ranking, same pipeline | OpenGeni doc and README; n not stated (inference: the same 26 questions) | unit of "points" not stated |
| bug-fix tasks | "no change in pass rate, cost or time" | tool off | 12 Terminal-Bench 2.1 + 12 SWE-rebench, one trial | "The agent called the tool about 0.4 times per task" |
| plain Codex CLI harness | "saved 16% cost and 11% time" | tool off | OpenGeni doc; n, CI, quality not stated in fetched text | not in genigrep README |
| Jev request latency | "about 0.4 seconds per request" | n/a | docs/how-it-works.md | measured by OpenGeni, no distribution |
| README example search | "evidence rating 0.94 / 15 passages from 10 files, ~10.5k tokens / 2.3s" | n/a | one example on the OpenGeni repo | illustrative, single run |

## Mechanism details you could implement
Thresholds and caps (src/engine/code-search/config.ts `DEFAULT_CODE_SEARCH_CONFIG`; header comment: "tuned on the E1 DEV split (2026-09-24); change them only with a new evaluation"):
```text
thresholds: T1 0.6 (file), T2 0.5 (passage), T3 0.5 (lead)
  "calibrated on the DEV split from the observed score distributions (relevant files mostly 0.6-0.9;
   minFiles and the lexical guard keep recall when few files pass)"
recall: maxCandidates 240, maxMatchesPerFile 25, testWeight 0.6, pathBonus 0.5, hitCountWeight 0.1, changelogWeight 0.6
wave1: filesPerRequest 60, hitLinesPerFile 3, hitLineChars 160, maxFiles 16, minFiles 8, lexicalGuard 5
wave2: windowsPerFile 5, maxUp 40, maxDown 120, maxWindowLines 150, passagesPerRequest 4, maxRequestChars 24000, maxPassages 80
wave3: maxLeadCandidates 60, maxLeadsFollowed 6, seedPassages 12
status: maxEvidenceChars 60000, hi 0.7, lo 0.4
pack: charsPerToken 3.2, minPassages 4, minRelevance 0.1, filePenalty 0.1, maxPassageChars 3200, changelogPrior 0.5, docPrior 0.85, lexWeight 0
```

Jev prompts (src/engine/code-search/judge.ts `PROMPTS`, "identical to scout-0.3.1"), verbatim:
- File task (state): "Code search triage for a software repository. A developer asked `question`. `files` lists candidate files found by keyword search; each entry is the file path followed by up to 3 matching lines as `line: text`. Judge each file independently by its path and matching lines."
- File criteria (stated once in state, "~65% fewer question tokens"): yes = "Reading this file would likely help answer the question: it probably implements, decides, computes, configures, enforces or documents the asked behavior. A doc or design note that explains the behavior counts." no = "The file probably only mentions the same words, imports or passes values through, belongs to an unrelated feature that shares keywords, or is a test that is not about the asked behavior."
- File noul: "Would reading file `files.<id>` (<path>) help answer the question: \"<q>\"? Apply `criteria`."
- Passage noul: "Does `passages.<id>` (<path> lines a-b) contain code or text needed to answer the question: \"<q>\"?" with true = "The passage implements, decides, computes, configures, enforces or documents part of the asked behavior. A helper that performs one asked step counts, and so does a doc passage that states the behavior." false = "The passage only mentions, imports, calls or passes through names related to the question, is a test or type declaration that does not show the behavior, or is unrelated code that shares keywords."
- Status noul: "Do the `evidence` passages show the answer to the question: \"<q>\"?" true = "Together the passages state or implement the answer concretely enough to cite file and line." false = "Some part of the answer is missing: the passages only mention the topic, or the deciding code is elsewhere."

Design rules (judge.ts header): "one state + many narrow Nouls per request (fan-out); one Noul per candidate (multi-select)"; "the literal question text is inlined in every question (no `collections[i]`-style indirection)"; "state holds only the candidates being judged (filtered by code first)"; "no counting, math or dates asked of Jev; code combines answers"; "A Jev failure is not replaced by lexical scores: it propagates and the whole search fails."

Agent-facing wording that fixed the quality loss (README "Instructions snippet"): "The rating cannot see what the search missed: use the passages instead of re-reading them, then check what they do not cover (other entry points, defaults, flags, exceptions) before concluding." Keywords: the evaluation used agent-chosen keywords (6-15), so the MCP tool makes `keywords` required.

## Limitations, caveats, counter-evidence
- README: "one repository in one language, 26 questions, one agent harness, and a small bug-fixing sample." The CLI, MCP server, skill and derived keywords "were not part of the evaluation". Question set, grading rubric, grader identity (human or model) and per-question results are not published.
- "Answer quality was equal" is stated from pass rate +1.9 points [-4.8, +8.7] on 26 questions; that interval is wide (inference: parity is "no detectable difference", not equivalence).
- Two runs report different CI wording between sources: README [-11.5, -1.9] vs OpenGeni doc "95% CI 2-12%"; consistent in substance.
- Thresholds were tuned on an internal DEV split (E1, 2026-09-24); whether the 26 evaluation questions are disjoint from DEV is not stated.
- Hosted API: passages up to 8,000 chars and up to 60,000 chars of packed evidence leave the machine; "genigrep does not scan file contents for secrets."
- Comparison with the bus note github-dzhng-jevgrep.md (title only read; content not in this workspace): jevgrep's -40% SWE-bench claim was questioned on n=500 sampling noise and on the saving disappearing after compaction drops the skill (context/reports/decision-trends.md lines 707, 710). genigrep reports a much smaller saving (~7%) with paired CIs and reports no effect on bug-fix tasks, so on bug fixing it points the other way from jevgrep's headline (inference). Both rely on the agent being told to call the tool.
- Instruction-bearing content: the repo ships agent instructions by design (skills/genigrep/SKILL.md, the README "Instructions snippet", MCP server instructions). They are product text for installed agents; they were read as evidence and not followed.

## Takeaways for tuning a memory stack
- For build-time reads over code, put the decision model after cheap lexical recall and before packing, as a per-item noul with explicit true/false criteria; keep a lexical guard (top 5 lexical always kept, top 8 judged always kept) so one judge miss cannot drop an obvious item.
- Fail closed on judge outage rather than falling back to lexical ranking if your own ablation shows a quality loss (here 7.7 points).
- Do not expose a sufficiency verdict as a stop signal to the agent; expose a number and say what it cannot see. This is the concrete failure mode for our assembly/stop rule (B9).
- Measure on investigation questions and on fix tasks separately; the gain here appeared only on investigation.
- Budget: about $0.006 of Jev per question versus a 6.6% cut in agent cost; the agent model dominates cost.

## Open questions
- What were the 26 questions, the grading rubric and the grader identities? Per-question quality deltas?
- Is the E1 DEV split disjoint from the 26 evaluation questions?
- Does the saving hold on larger or polyglot repos, and with keywords derived rather than agent-chosen?
- The Codex CLI result (16% cost, 11% time): n, CI, quality?

## Grading and labels
- Directness: high. Jev reranks code evidence for a coding agent on a real monorepo.
- Control: medium. Paired on/off, blind graders, bootstrap CIs, keyword-only ablation; only run 1 is significant alone.
- Independence: low. Builders on their own repo and tool; graders not identified.
- Reproducibility: low. Engine, prompts and thresholds pinned; question set and grades not published.
- Applicability: medium. Matches our build-time code reads; one TypeScript repo, investigation questions only.
- Pillars: R9 primary (Jev at a memory stage on an engineering workload); R3 (retrieval and context assembly), R6 (evaluation design, wording effect).
- Stage: reranking (Jev filters and ranks what ripgrep recall returns; also a sufficiency rating at assembly).
- Tags: mechanism jev-noul-judge, lexical-guard, sufficiency-rating; workload coding-agent code investigation.
- B11 supports: the lexical guard and "minFiles" exist so a judge cannot prune gold evidence; fallback-free failure also shows the judge matters.
- B20 supports: the post's headline narrows on a primary read (harness not the CLI, one significant run, no bug-fix effect).
- Contradiction: B9 (qualified). A sufficiency label used as a stop cue saved 15% but lost answers; parity came back only after rewording, at about half the saving. Evidence that a sufficiency stop rule can cost accuracy when surfaced to the agent.
- would_create: tool wording about a decision-model score changes agent stopping behaviour and answer quality.

## Origin chain
@bendikdev post (2026-09-28, links http://github.com/Cloudgeni-ai/genigrep) -> genigrep README "Measured results" and docs/how-it-works.md at `da10c5e` -> README cites OpenGeni docs/code-search.md for methodology (fetched) -> engine ported from OpenGeni packages/jev at `fe7ea0a` (NOTICE). Independence: all sources are the builder (Cloudgeni-ai); the reply post adds no evidence.
