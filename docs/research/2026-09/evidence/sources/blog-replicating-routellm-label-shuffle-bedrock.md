---
schema_version: 1
artifact_id: N-20260926-03
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103259862985752788", "file_id": null, "sha256": null}, {"artifact_id": "post:2103087820109910385", "file_id": null, "sha256": null}, {"artifact_id": "post:2103186703955730872", "file_id": null, "sha256": null}, {"artifact_id": "post:2103666796309979253", "file_id": null, "sha256": null}, {"artifact_id": "post:2103439275354436043", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:brianfeeny.com/posts/replicating-routellm-on-amazon-bedrock
claim_cluster: url:brianfeeny.com/posts/replicating-routellm-on-amazon-bedrock
feeds: ["decision"]
primary_source: https://brianfeeny.com/posts/replicating-routellm-on-amazon-bedrock/
source_commit: 4577252b108ec70fc9f8d81edac7ac2329cc08d8
strength: repo-pinned
pillar_primary: R6
pillar_secondary: ["R4"]
tags: {"mechanism": ["prompt-only router", "label shuffle control", "leave-one-group-out", "response-based deferral"], "workload": ["model routing", "academic QA benchmarks"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: the author trained the routers and reports the shuffle and held-out-group AUCs", "control": "high: within-group label shuffle and leave-one-group-out are exactly the controls needed", "independence": "medium: independent of RouteLLM authors; single author; uses RouteLLM's public labels", "reproducibility": "high: code at a pinned commit with CloudFormation and Makefile; cached embeddings", "applicability": "medium: routing and escalation classifiers in our stack (H5 two-tier, admission gates) face the same group-memorisation risk; benchmarks are academic, not engineering traffic"}
beliefs_affected: {"supports": ["B13", "B20"], "contradicts": [], "would_create": ["A prompt-only difficulty or escalation classifier evaluated with item-level splits mostly learns task-group membership; only group-held-out evaluation shows whether it predicts difficulty"]}
claim_correction: The post says a router "trained on 110k labels" scored 0.84 and still 0.838 after shuffling; in the write-up the 0.842 / 0.838 pair is the BBH cascade-label set (2,430 items, 27 tasks, linear probe), while the 109,101 RouteLLM battle labels gave 0.706 on a 16,595-item hold-out with no shuffle result reported.
---

# Replicating RouteLLM on Amazon Bedrock (Brian Feeny)

- **URL:** https://brianfeeny.com/posts/replicating-routellm-on-amazon-bedrock/ ; code https://github.com/bfeeny/paper-to-aws-routing
- **Type:** builder writeup + repo
- **Author / org:** Brian Feeny
- **Date:** 2026-09-21
- **Retrieved:** 2026-09-26; repo HEAD `4577252b108ec70fc9f8d81edac7ac2329cc08d8` (2026-09-23) via GitHub API; not cloned
- **Cited by evidence:** https://x.com/brianfeeny/status/2103259862985752788 (@brianfeeny). Related RouteLLM promotion posts narrowed by this note: https://x.com/hooshaaii/status/2103087820109910385 (@hooshaaii, RouteLLM arXiv 2406.18665), https://x.com/GoodThingStudio/status/2103186703955730872, https://x.com/kysstalol/status/2103666796309979253, https://x.com/hooshaaii/status/2103439275354436043
- **Relevance to a memory stack:** medium-high. Any classifier we put in front of a costlier step (escalate to tier 2, recall or not, admit or not) can pass an item-level eval by recognising the task family. This gives the two controls that expose it.

## TL;DR
- Prompt-only routers mostly learn **which group a request comes from and that group's escalation base rate**, not whether the cheap model will succeed.
- Within-group label shuffle keeps almost all AUC: BBH 0.838 shuffled vs 0.842 real (99.5% retained); mixed set 0.643 vs 0.744 (86%); MATH 0.626 vs 0.674 (93%).
- Leave-one-group-out (LOGO) AUC collapses to about chance: BBH 0.525 (group oracle 0.545), mixed 0.558 (0.533), MATH 0.600 (0.569).
- Response-based **deferral** (features of the cheap model's own output: token count, truncation, answer markers) does better on LOGO: MATH 0.752 vs 0.600 prompt-only, mixed 0.670 vs 0.558; output token count alone 0.757 on MATH.
- On MT-Bench, "category identity alone reaches AUC 0.693" while routers on a held-out category average 0.522.
- **Claim correction:** the viral "110k labels, 0.84 -> 0.838" merges two label sets (see frontmatter).

## What it claims / describes
- **Labels.** Cascade labels: for each item query Claude Haiku 4.5, Sonnet 4.6 and Opus 4.5 in order and stop at the first tier whose answer grades exactly correct; label y = 1 if escalation changed the outcome. Plus RouteLLM's 109,101 GPT-4 vs Mixtral preference battles.
- **Data.** Mixed set 2,709 items over GSM8K, MMLU, MMLU-Pro, BBH, MATH L4-5; BBH all 27 tasks 2,430 items; MATH levels 1-5 2,520 items.
- **Routers.** (1) linear probe: Titan Text Embeddings V2 256-d -> L2 logistic regression; (2) RouteLLM similarity-weighted ranking; (3) fine-tuned bge-small-en-v1.5 (33M); (4) prompt length alone.
- **Controls.** Within-group label permutation that preserves each group's base rate; leave-one-group-out; a group-oracle that predicts the group's training escalation rate.
- **Deployment.** JSON weights inside an Amazon Bedrock AgentCore Gateway REQUEST interceptor on Lambda: one Titan embedding call plus a 256-term dot product, about 110 ms end to end.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| in-distribution AUC, mixed | 0.744 | | 2,709 items | |
| in-distribution AUC, BBH (linear probe) | 0.842 | | 2,430 items, 27 tasks | |
| in-distribution AUC, MATH (fine-tuned encoder) | 0.865 | | 2,520 items | |
| within-group shuffled AUC | BBH 0.838; mixed 0.643; MATH 0.626 | real 0.842 / 0.744 / 0.674 | permutation within group | MATH real here is 0.674 (different router than the 0.865 row) |
| LOGO AUC router vs group oracle | BBH 0.525 vs 0.545; mixed 0.558 vs 0.533; MATH 0.600 vs 0.569 | | leave-one-group-out | CIs reported as differences: -0.021, +0.025, +0.031 |
| RouteLLM battle labels, linear probe | 0.706 | | 16,595-item hold-out of 109,101 | no shuffle reported |
| deferral AUC on LOGO | MATH 0.752; mixed 0.670 | prompt-only 0.600 / 0.558 | Haiku response features | |
| output tokens alone | 0.757 | | MATH LOGO | |
| label test-retest agreement | Haiku kappa 0.973; Sonnet 0.897; Opus 0.878 | | repeated grading | ceiling AUC 0.912 |
| cost, Haiku -> Opus, price ratio R = 5 | always-strong 5.00x; perfect deferral 1.61x (68% saving) | | cost model | perfect deferral is an upper bound |
| MT-Bench | category identity AUC 0.693; routers on held-out category 0.522 | | | |

## Mechanism details you could implement
- For every gating classifier (tier-2 escalation, recall/no-recall, admission), run two extra evaluations before trusting it: (a) **within-group label shuffle** preserving base rates: if AUC barely moves, the model is recognising the group; (b) **leave-one-group-out**, grouping by repository, task family or author.
- Compare against a **group-oracle** baseline (predict the group's training rate). A router that does not beat it adds nothing.
- Prefer **response-based deferral** where possible: run the cheap tier, then decide on features of its output (length, truncation, marker count). Costs no extra inference.
- Measure label noise first (test-retest kappa) to set the achievable ceiling (here 0.912).

## Limitations, caveats, counter-evidence
- Author's list: exact-graded academic benchmarks, not production traffic; small fine-tuned model (33M); preference labels from one model pair; some cells under 50 positives; offline on cached embeddings; exploratory, not preregistered.
- Group structure in real engineering traffic (repos, task types) may be weaker or stronger than benchmark groups (inference).
- RouteLLM's own claims were not re-evaluated on RouteLLM's exact MT-Bench protocol beyond the category analysis above.

## Takeaways for tuning a memory stack
- Our H5 two-tier escalation and any admission classifier should be evaluated leave-one-repository-out plus a shuffle control; item-level splits will flatter them.
- jevmem's "tier 2 below tier 1 on held-out" (B13) is consistent with escalation signals not generalising across groups (inference).
- Consider escalation on the cheap tier's output, not on the input.

## Open questions
- Does a decision model (Jev-style) router show the same group memorisation? Not tested here.
- How large is the group effect on engineering-agent traffic grouped by repository? Unknown.

## Grading and labels
- Directness high; control high; independence medium; reproducibility high (commit 4577252b); applicability medium.
- Pillar R6 (whether an evaluation supports its conclusion: leakage via group identity); secondary R4 (routing/escalation as a decision).
- Beliefs: supports B13 (escalation is not automatically better; evaluate on the right population), supports B20 (headline claims narrow on a primary read; the post itself misstates the label set). Would create the group-memorisation belief above.
- Contradiction rows: none against held beliefs. It narrows RouteLLM's published MT-Bench gains (external claim), which the RouteLLM promotion posts in this cluster repeat uncritically.

## Origin chain
post 2103259862985752788 -> brianfeeny.com write-up (2026-09-21) -> sections on label shuffle, LOGO, deferral, MT-Bench -> repo bfeeny/paper-to-aws-routing @ 4577252b. The four RouteLLM posts point to arXiv 2406.18665 (RouteLLM, 2024), whose MT-Bench result this write-up re-examines. Independence: author unaffiliated with RouteLLM; uses RouteLLM's released labels (shared dataset).
