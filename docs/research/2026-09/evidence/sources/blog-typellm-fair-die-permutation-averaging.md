---
schema_version: 1
artifact_id: N-20260926-09
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2102654986475979216", "file_id": null, "sha256": null}, {"artifact_id": "post:2102652264431353918", "file_id": null, "sha256": null}, {"artifact_id": "post:2102655854386483214", "file_id": null, "sha256": null}, {"artifact_id": "post:2102654999247655343", "file_id": null, "sha256": null}, {"artifact_id": "post:2102654995359572425", "file_id": null, "sha256": null}, {"artifact_id": "post:2102341093472010266", "file_id": null, "sha256": null}, {"artifact_id": "post:2102452813163085917", "file_id": null, "sha256": null}, {"artifact_id": "post:2102453041840718081", "file_id": null, "sha256": null}, {"artifact_id": "post:2102652260727882084", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:typellm.ai/blog/fair-die
claim_cluster: url:typellm.ai/blog/fair-die
feeds: ["decision"]
primary_source: https://typellm.ai/blog/fair-die
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R4
pillar_secondary: ["R3"]
tags: {"mechanism": ["choice question", "option-order bias", "permutation averaging", "KV-cache reuse"], "workload": ["probabilistic choice over a closed option set", "listwise rerank"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: all 720 orderings enumerated for both models", "control": "medium: exhaustive permutation control, but one toy question with a known answer", "independence": "low: TypeLLM is a competing typed-decision product and sells the fix", "reproducibility": "medium: example script path given (examples/fair_die/fair_die.py); repo URL and commit not captured; pijev repo 404 at the guessed URL", "applicability": "medium: our listwise rerank (B10) and memory-kind choices use the same choice interface; a die is not a relevance task"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Choice probabilities from decision models can carry option-identity or position bias; for a generative model, averaging 8 orderings removed about 79% of the error, but it did not fix Jev's label bias"]}
claim_correction: The pijev thread says reordering choices changes Jev's probabilities and permutation averaging improves them; the TypeLLM report shows Jev's bias follows the label "one" (77-91% wherever it appears), so averaging barely helped Jev (86.01% for "one" after all 720 orderings); the large gains are for Qwen, which is position-biased.
---

# Can Jev roll a die? Permutation averaging for decision-model probabilities (TypeLLM blog)

- **URL:** https://typellm.ai/blog/fair-die (retrieved via ?v=1)
- **Type:** vendor blog (TypeLLM, a competing typed-decision client/serving product)
- **Author / org:** TypeLLM; no individual author credited; posts by Mingtian Zhang (@mingtianzhang)
- **Date:** 2026-09-22
- **Retrieved:** 2026-09-26; example script `examples/fair_die/fair_die.py` referenced, repo URL not captured; `github.com/mingtianzhang/pijev` returned 404
- **Cited by evidence:** https://x.com/mingtianzhang/status/2102654986475979216, /2102652264431353918, /2102655854386483214, /2102654999247655343, /2102654995359572425, /2102341093472010266 (pijev), /2102452813163085917, /2102453041840718081, /2102652260727882084 (all @mingtianzhang)
- **Relevance to a memory stack:** medium. Our rerank design rests on one Jev choice call over a candidate pool (B10). Any systematic bias in choice probabilities by option identity or position directly biases recall@1.

## TL;DR
- Question: which face of a fair six-sided die lands up; ideal 16.67% each. **Jev gave "one" 83%** with others at 1 to 8%.
- Over **all 720 orderings**, "Jev kept favoring `one`, wherever it appeared" at 77 to 91%: a label bias, not a position bias.
- Qwen (served via TypeLLM) favoured whichever option came first in "718 of 720 orderings": a position bias.
- Permutation averaging over all 720: Jev still 86.01% for "one"; Qwen 13.47 to 25.41% per face. For Qwen, "averaging 8 permutations reduced error by 79%", 97% with all 720.
- TypeLLM ships `"permutations": 8` or `"all"` on enum questions; pijev is a TypeSafe-compatible client doing the same for Jev.
- **Claim correction:** permutation averaging is the fix for position bias (Qwen); for Jev the bias followed the label and averaging did not remove it.

## What it claims / describes
- Test prompt: "what number will come up on a single roll of a fair six-sided die?" with six categorical options.
- Diagnostic: enumerate all option orderings to separate label bias (bias follows the text) from position bias (bias follows the slot).
- Fix: average the probability each option gets across orderings; batch orderings in one call and reuse the shared-prefix KV cache (SGLang) to keep cost down.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| Jev P("one"), original order | 83% | ideal 16.67% | 1 ordering | toy question |
| Jev P("one") across orderings | 77 to 91% | | 720 orderings | label bias |
| Qwen first-slot preference | 718 of 720 orderings | | 720 | position bias |
| Jev after averaging all 720 | 86.01% for "one" | 16.67% | | no fix |
| Qwen after averaging all 720 | 13.47 to 25.41% per face | 16.67% | | |
| Qwen error reduction, 8 permutations | 79% | no averaging | | error metric not specified in fetched text |
| Qwen error reduction, 720 permutations | 97% | | | |

## Mechanism details you could implement
- **Order audit:** for any choice question we depend on (rerank pool, memory kind, route), rerun with shuffled option orders on a labelled sample; compare the distribution of the chosen option's rank. If the winner tracks position, average over k orderings; if it tracks label text, rephrase or neutralise labels (e.g. opaque ids).
- **Permutation averaging:** k = 8 random orderings captured most of the gain for a position-biased model; cost is k calls or one batched call with prefix caching.
- Use opaque candidate ids (as jevmem does with 6-char ids) rather than descriptive option labels where possible (inference).

## Limitations, caveats, counter-evidence
- One toy question with a known uniform answer; not a relevance or routing task.
- The report "doesn't fully explain Jev's semantic preference for 'one'" nor whether it generalises across choice sets.
- Vendor independence is low: TypeLLM sells the permutation feature and a competing base model.
- Error metric for the 79% / 97% figures not captured.

## Takeaways for tuning a memory stack
- Add an order-shuffle control to H5-rerank: measure recall@1 of the single choice call with the candidate list in retrieval order vs shuffled vs averaged over 8 orderings.
- Candidate labels in a rerank should be ids, not prose, to reduce label bias (inference).

## Open questions
- Does Jev show position bias on relevance tasks with long candidate texts (as opposed to label bias on a toy)? Not tested.
- Does the Hindsight 0.94 recall@1 (B10) depend on candidates arriving in RRF order? Not tested anywhere we know.

## Grading and labels
- Directness high; control medium; independence low; reproducibility medium; applicability medium.
- Pillar R4 (decision-model probabilities as a decision input). Secondary R3 (listwise rerank).
- Beliefs: supports B14 (probabilities are not calibrated by default: 83 to 91% on a uniform event). Bears on B10 (single choice call rerank) as an untested confound, not a contradiction. Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
posts by @mingtianzhang (nine, one thread plus quotes) -> typellm.ai/blog/fair-die (2026-09-22) -> sections "initial results", "720 orderings", "permutation averaging", "efficiency" -> this note. The pijev post (2102341093472010266) has no link; merged into this cluster because it repeats the same claim by the same author. Independence: single author/org, competing vendor.
