---
schema_version: 1
artifact_id: N-20261001-01
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105191816136122402", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:caura-ai/caura-locomo
claim_cluster: github:caura-ai/caura-locomo
feeds: ["memory"]
primary_source: https://github.com/caura-ai/caura-locomo
source_commit: c55d3a3fe8df01533690c7f2e6874e6a0e67c9be
strength: repo-pinned
pillar_primary: R6
pillar_secondary: ["R3"]
tags: {"mechanism": ["full-context baseline", "random-selection retrieval baseline", "two-sided abstention scoring", "prompt provenance hashing"], "workload": ["chat memory", "LoCoMo"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-question results, judge verdicts and prompt hashes are committed in outputs/", "control": "medium: random-selection and full-context controls, 3 runs for one configuration, but prompts tuned on the reported questions", "independence": "medium: independent of mem0/Zep/Letta vendors, but reuses mem0's judge prompt and a generous GPT-4o judge", "reproducibility": "high: MIT runner, dataset sha256 pinned, commands in REPRODUCE.md", "applicability": "low: chat-memory benchmark, 10 public conversations, no engineering artifacts"}
beliefs_affected: {"supports": ["B19", "B20"], "contradicts": [], "would_create": ["On public LoCoMo (10 conversations) a no-retrieval full-context reader scores about 87% judge-accepted, so a LoCoMo memory score is unreadable without a full-context and a random-selection line beside it"]}
claim_correction: The post's 87.27% is a no-retrieval full-context baseline with a gpt-5-mini reader, not a Caura memory score; the repo contains no retrieval-backed QA score for Caura, and Caura's own retrieval evidence-hit is close to random selection (45.76% vs 42.30% at k=10).
memory_stage: evaluation
priority: 4
---

# Caura on LoCoMo: a full-context baseline, and what it costs to read one (caura-ai/caura-locomo)

- **URL:** https://github.com/caura-ai/caura-locomo (write-up linked from the post: https://caura.ai/blog/locomo-open-benchmark, not read; the repo is the primary source)
- **Type:** repo
- **Author / org:** Caura (CauraAI); MIT licence
- **Date:** HEAD commit c55d3a3fe8df01533690c7f2e6874e6a0e67c9be, 2026-09-28 14:14:05 +0300, "fix: tests no longer git-clone, and advertised env vars are actually read"
- **Retrieved:** 2026-10-01 (local shallow clone: repos/caura-locomo). Read: README.md, REPRODUCE.md, outputs/ listing. Code not executed.
- **Cited by evidence:** @CauraAI, 2026-09-30, https://x.com/CauraAI/status/2105191816136122402 ("87.27% on LoCoMo (full context, 1,344/1,540) ... in under 8 minutes for about $3")
- **Relevance to a memory stack:** high for evaluation design (priority 4: memory benchmarks). It is the cleanest public statement so far that a LoCoMo score needs two control lines (full context, random retrieval) and two-sided abstention scoring before it means anything.

## TL;DR
- **Claim correction:** 87.27% is not a memory-system score. README line 5: "The headline is a **baseline, not a system score**: with the entire conversation in the prompt and **no retrieval at all**, a gpt-5-mini reader answers **87.27%** of LoCoMo's scored questions (1,344 / 1,540) under a single-pass GPT-4o judge."
- Caura's own retrieval, measured as evidence-hit, is barely above random session selection: 45.76% vs 42.30% random at k=10, and below random on multi-hop (60.28% vs 67.78%) and open-domain (42.39% vs 47.74%) (REPRODUCE.md lines 72 to 77). The README says plainly: "No end-to-end retrieval-backed QA result is included here."
- The harness adds three things we should copy into our own benchmark: a random-selection retrieval baseline, abstention scored on both classes (correct refusal 76.23% on 446 unanswerable, false refusal 6.49% on 1,540 answerable), and prompt hashes in every result file.
- Prompt choice alone moved the score by 24.61 points with reader and judge fixed (48.18% to 72.79%), and prompts were selected on the same 1,540 questions reported. Judge-accepted, not verified correct.
- Cost: a full 1,986-question pass is 7 to 8 minutes and about $3; median reader input 19,248 tokens with 97.66% cached.

## What it claims / describes
A Python CLI (`locomo`) that runs LoCoMo (snap-research `locomo10.json`, sha256 `79fa87e9...8ff4`, checked by `locomo verify`) in three arms:

| arm | context given to the reader | cost |
|---|---|---|
| `fullcontext` | the entire conversation | ~19.2k tokens/question |
| `retrieval` | top-k sessions from the store | k x ~2.6k chars |
| `recall` | none, evidence-hit only, no LLM calls | free |

Reader `gpt-5-mini` at temperature 1 (the model does not accept 0). Headline judge `gpt-4o` single pass, secondary `gpt-4o-mini`; judge prompt is mem0's, "as published in its benchmark harness at the time of our runs". Caura 3.9.0 local deployment for the retrieval arms.

Dataset as published: 10 conversations (the paper describes 50), 1,986 questions: multi-hop 282, temporal 321, open-domain 96, single-hop 841, adversarial 446; scored categories 1 to 4 = 1,540. "Several published harnesses ship this mapping inverted; `tests/test_dataset.py` pins it against the file."

Category 5 (adversarial) handling: "LoCoMo's category 5 is usually excluded on the stated grounds that ground truth is unavailable; in fact all 446 items carry an `adversarial_answer` field. Scoring it only works if abstention is offered to *both* classes, which `--abstain-all` does; otherwise 'abstain iff category 5' scores 100%." (README, punctuation adapted.)

Random-selection line: `locomo baseline` prints the expected evidence-hit rate if k sessions were drawn uniformly. "With ~27 sessions per conversation, k=50 reaches 96% of the store by construction, so a retrieval number is unreadable without this line beside it."

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| QA accuracy, uniform prompt | 87.27% (1,344/1,540) | 87.08% under GPT-4o-mini judge | full context, no retrieval, gpt-5-mini reader, cats 1 to 4 (README line 9, REPRODUCE line 28) | single run; generous judge; prompts tuned on same set |
| QA accuracy, category-routed prompt | 87.71% +/- 0.36 (GPT-4o judge), 88.27% +/- 0.31 (GPT-4o-mini) | uniform 87.27% | 3 runs: 88.05 / 87.73 / 87.34 | routed minus uniform +0.43 pp, "an observed difference between configurations rather than an isolated effect of routing" |
| mem0 paper full-context baseline (cited) | 72.90% | "higher than every memory system it evaluated" | gpt-4o-mini reader, GPT-4o judge (README line 12) | second-hand citation |
| another study (cited) | 92.85% | n/a | gpt-5-mini reader, three-vote generous judge | second-hand, study not named in README |
| correct refusal | 76.23% (340/446) | n/a | `--abstain-all` prompt, all 1,986 questions (REPRODUCE line 49) | two of 446 carry a real answer ("No") and are scored wrong |
| false refusal | 6.49% (100/1,540) | n/a | same (line 50) | |
| cats 1 to 4 accuracy under abstain prompt | 81.30% | 87.27% without abstention | same (line 51) | "Two runs, two prompts; an observed difference, not a measured causal cost" |
| evidence-hit k=3 / 5 / 10 / 20 | 13.62 / 24.82 / 45.76 / 77.95% | random 13.83 / 22.42 / 42.30 / 76.77% | Caura 3.9.0 local, 1,982 questions with evidence (lines 72 to 75) | one local deployment; candidate ids not retained |
| evidence-hit k=10, multi-hop | 60.28% | random 67.78% | same (line 77) | below random |
| evidence-hit k=10, open-domain | 42.39% | random 47.74% | same | below random |
| distinct result sets | 75 distinct ordered sets across 1,986 questions; two conversations returned an identical set for every question | n/a | same | suggests a degenerate retriever (inference) |
| prompt progression | v1 48.18%, v2 59.61%, v3 72.79% | reader and judge fixed at gpt-4o-mini | +24.61 points (lines 87 to 89) | prompt snapshots not retained for these runs |
| run cost | about $3, 7 to 8 min at concurrency 32 | n/a | 1,986 questions | median reader input 19,248 tokens, 97.66% cached |

## Mechanism details you could implement
- **Three arms, same questions:** full context (upper reference for small corpora), retrieval at k, and a no-LLM recall arm that scores evidence-hit only. The recall arm is free, so sweep k = 3, 5, 10, 20, 50.
- **Random-selection line next to every retrieval number:** expected hit if k units were drawn uniformly from the conversation's store. Report observed minus random, per category.
- **Two-sided abstention:** offer abstention on every question (`--abstain-all`) and report correct-refusal rate on unanswerable items and false-refusal rate on answerable ones. Never score "abstain iff category 5".
- **Degeneracy check:** count distinct ordered result sets across all questions (`scripts/degeneracy.py`). A retriever that returns the same set for every question in a conversation is broken whatever its hit rate.
- **Provenance per result file:** prompts, prompt hashes, routing configuration, reader and judge model ids; a test (`tests/test_prompts.py`) fails if benchmark content appears in a reader-facing prompt (added after an earlier prompt contained two gold answers as style examples).
- **Dataset digest check** before quoting a number (`locomo verify`); re-serialising JSON changes the digest.

## Limitations, caveats, counter-evidence
- Stated in REPRODUCE.md: prompts were selected on the same 1,540 questions reported (no held-out split; LoCoMo defines none); the judge prompt "instructs the grader to be generous", so read as judge acceptance; text only (image captions excluded); 10 of 50 conversations; retrieval measured on one local deployment with candidate ids not retained; "No end-to-end retrieval-backed QA result is included here."
- REPRODUCE.md cites Penfield: a gpt-4o-mini judge accepted 62.81% of deliberately wrong answers, and 99 answer-key errors in the 1,540 scored questions; Caura did not reproduce that audit.
- The uniform headline is a single run; the +/- applies to the routed configuration only.
- Reader and judge are both OpenAI models (gpt-5-mini reader, GPT-4o judge): same vendor, different models (inference: some shared bias is possible).
- The vendor publishes this as a baseline while its own retrieval looks near random; the repo is candid about that, which raises trust in the harness, not in the product.

## Takeaways for tuning a memory stack
- Any memory number we publish (or accept from a vendor) on LoCoMo must sit next to a full-context line on the same reader and judge. On LoCoMo-10 the full-context line is about 87%; a memory system scoring below it is buying cost or latency, not accuracy.
- Report retrieval as observed minus random at the same k, per question category. Our PDLC benchmark (priority 4) should carry this from day one, because engineering stores also have few units per project.
- Score abstention on both classes. A recall gate that always abstains on a known-unanswerable category is not a gate.
- Hash and store prompts with results; freeze prompts before scoring and keep a held-out split (LoCoMo has none, so build one).

## Open questions
- What does Caura's retrieval-backed QA arm score? Not in the repo.
- How much of the 87.27% survives a strict judge or Penfield's corrected answer key?
- Does the random-selection line stay this close on longer stores (LongMemEval-M, engineering corpora with hundreds of sessions)?

## Grading and labels
- **Directness: high.** Per-question answers, both judges' verdicts, prompt hashes and configuration are committed (`outputs/*/results.json`).
- **Control: medium.** Full-context and random-selection controls, three runs for one configuration, prompts held fixed in the progression study; but prompt selection on the reported set and a generous judge.
- **Independence: medium.** Not a memory-vendor comparison table; reuses mem0's judge prompt; second-hand citations (mem0 72.90%, unnamed 92.85%) not checked here.
- **Reproducibility: high.** MIT, pinned dataset digest, exact commands, outputs committed.
- **Applicability: low.** Chat memory, short stores, no engineering artifacts; the method (controls, two-sided abstention, provenance) transfers fully.
- **Pillars:** R6 primary (whether a LoCoMo score supports its conclusion); R3 secondary (retrieval evidence-hit vs random). **Memory stage:** evaluation. **Priority:** 4.
- **Beliefs:** supports B19 (label leakage is real: the repo found and removed gold answers in a reader prompt); supports B20 (the post's headline narrows on a primary read: baseline, not system score). Would create: "On public LoCoMo a full-context reader scores about 87% judge-accepted; memory scores need full-context and random-selection lines."
- **Contradictions:** none with the register or the synthesis.

## Origin chain
Post @CauraAI 2105191816136122402 (2026-09-30) -> github:caura-ai/caura-locomo at c55d3a3 -> README.md lines 5 to 12 (headline, comparison), REPRODUCE.md lines 28 (headline), 49 to 51 (abstention), 72 to 77 (retrieval vs random), 87 to 89 (prompt progression), 94 to 101 (limitations) -> this note. Independence: shares the mem0 judge prompt with mem0's published LoCoMo runs; the 72.90% figure is mem0's own; no shared authors with Tiger Data (N-20260929-12) or HivemindOS (N-20260928-09) LoCoMo notes as far as stated.
