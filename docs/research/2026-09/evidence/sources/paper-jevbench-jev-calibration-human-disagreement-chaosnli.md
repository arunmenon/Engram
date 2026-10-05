---
schema_version: 1
artifact_id: N-20260929-19
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104787527391482063", "file_id": null, "sha256": null}, {"artifact_id": "post:2104787761609732582", "file_id": null, "sha256": null}, {"artifact_id": "post:2104797306113388591", "file_id": null, "sha256": null}, {"artifact_id": "post:2104795816925798870", "file_id": null, "sha256": null}, {"artifact_id": "post:2104777143482044927", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:zenodo.org/records/22971492
claim_cluster: url:zenodo.org/records/22971492
feeds: ["decision", "memory"]
primary_source: https://zenodo.org/records/22971492
source_commit: dd010299221ac7232b08407d59c4398d47192547
strength: paper-single-benchmark
pillar_primary: R9
pillar_secondary: ["R4", "R6"]
memory_stage: none
priority: 1
tags: {"mechanism": ["calibration", "confidence-thresholding", "temperature-scaling", "choice-vs-noul-primitive", "ambiguity-detection"], "workload": ["nli", "chaosnli", "human-label-variation"], "lifecycle_stage": ["write_gate", "recall_gate", "linking", "evaluation"], "cross_cutting": ["preregistration", "bias-corrected-ece", "vendor-claim-audit", "independent-replication"]}
evidence_grade: {"directness": "high: directly tests whether Jev (TypeSafe) probabilities stay calibrated when humans disagree, the property our gate thresholds assume", "control": "high: preregistered hashed plan, equal n=750 per stratum, parametric bias correction validated by simulation (FPR 0.051), M-bin sweep, soft and hard scoring, paraphrase contamination control; two post-data fixes disclosed", "independence": "high: independent author (not affiliated with TypeSafe), labels are 100 public human annotations per item, no LLM judge; TypeSafe supplied $5 of API credit", "reproducibility": "medium: code, locked item ids, per-bin results JSON and hashes public at pinned commit; raw Jev responses and sentence text not in repo, rerun needs a TypeSafe key and jev-1.13.0 may not stay served", "applicability": "medium: one task (3-way NLI on SNLI/MNLI sentence pairs), one model version; our gates ask different questions over long PDLC artifacts, but the failure mode (confident on contested inputs) transfers as a hypothesis"}
beliefs_affected: {"supports": ["B14", "B13"], "contradicts": [], "would_create": ["Jev Choice probabilities (jev-1.13.0) are near calibrated on low-disagreement inputs but overconfident on contested ones (soft ECE 0.076 vs 0.339); 1 - top probability ranks contestedness (AUROC 0.744)", "Choice and normalised three-Noul primitives from the same Jev call have different calibration behaviour (corrected dECE 0.264 vs 0.076); primitive choice is a design variable", "One global temperature cannot calibrate both clear and contested strata (T=11.94 fixes contested 0.339 to 0.044, breaks clear 0.081 to 0.198)"]}
claim_correction: Post 2104777143482044927 says "297 questions where humans only agreed ~47%... started at 96%"; in the source 81% vs 47% is over all 750 contested items, and 297 is the number of contested items in the 0.9-1.0 confidence bin (mean confidence 0.962, soft agreement 0.505); "NLI model worse" refers to BART-MNLI, a supervised in-domain reference the preregistration says not to tabulate against Jev
---

# Confident Where People Disagree: preregistered test of Jev (TypeSafe) calibration against human disagreement on ChaosNLI (jevbench)

- **URL:** https://zenodo.org/records/22971492 (paper v1.0, DOI 10.5281/zenodo.22971492); concept DOI 10.5281/zenodo.22971491; v1.1 at https://zenodo.org/records/23032384 (29 Sep 2026, "adds missing related work ... No data or results changed", README.md:7); preregistration DOI 10.5281/zenodo.22971413; code https://github.com/GautamTalksDev/jevbench
- **Type:** paper (Zenodo preprint, not peer reviewed) plus repo
- **Author / org:** Gautam Khosla (Computer Engineering, University of Ottawa; "independent study. Not affiliated with or endorsed by TypeSafe AI or the University of Ottawa", docs/WRITEUP.md:7, :75). Licences CC BY 4.0 and MIT.
- **Date:** paper v1.0 published 26 Sep 2026 (Zenodo record). Scored run id `exp1_difficulty_calibration_20260925T070159Z_84db02c9` (results/exp1.json:1038), i.e. 25 Sep 2026. Model pinned `jev-1.13.0`, serving path `native` (https://api.typesafe.ai, jevbench/clients/jev.py:26, :33), price snapshot 2026-09-19 (experiments/exp1_difficulty_calibration.yaml:6).
- **Retrieved:** 2026-09-29. Repo shallow clone at `repos/jevbench`, commit `dd010299221ac7232b08407d59c4398d47192547` (2026-09-29 03:11:52 -0400, "docs: update the CI note now that CI runs again"). Read: README.md, docs/WRITEUP.md, PREREGISTRATION.md, docs/PREREG_CHANGELOG.md, experiments/exp1_difficulty_calibration.yaml, results/exp1.json, results/exp1_s1.json, results/exp1_s3.json, results/exp1_bart_fix.json, results/exp1_baselines.json (partial), jevbench/clients/jev.py (partial). Zenodo record page read via WebFetch; the PDF itself was fetched but the fetch tool could not extract its text (compressed binary), so paper-body locators below are replaced by the repo's committed result files and the author's write-up, which states "Every number here comes from the paper" (docs/WRITEUP.md:3). Every headline number matches the Zenodo abstract.
- **Cited by evidence:** @HeyGautamTalks (the author), five replies/posts on 2026-09-29: https://x.com/HeyGautamTalks/status/2104787527391482063, https://x.com/HeyGautamTalks/status/2104787761609732582, https://x.com/HeyGautamTalks/status/2104797306113388591, https://x.com/HeyGautamTalks/status/2104795816925798870 (decision feed), https://x.com/HeyGautamTalks/status/2104777143482044927 (memory feed). This note resolves the cluster parked in an earlier run under x:2104435470620848342 for lack of a primary source: the primary source is now the Zenodo paper plus the pinned repo.
- **Relevance to a memory stack:** high. Every Jev-driven gate in a memory stack (write gate, supersession, recall gate, staleness audit) thresholds Jev probabilities as if calibrated; this is the first preregistered, independent test showing where that assumption breaks.

## TL;DR
- On ChaosNLI (public NLI set, 100 human annotations per item), Jev `jev-1.13.0` Choice probabilities were close to calibrated on the 750 lowest-disagreement items (soft ECE 0.076; mean confidence 0.915 vs 0.844 annotator share) and overconfident on the 750 highest-disagreement items (soft ECE 0.339; mean confidence 0.807 vs 0.468). Bias-corrected dECE 0.264, 95% interval 0.244 to 0.278, p < 1/2001; preregistered verdict "tracks" (threshold 0.09).
- The same question asked as three normalised Nouls in the same call degraded much less (corrected dECE 0.076, verdict "inconclusive"). The posts omit this arm; the paper insists "neither is 'the' result".
- 1 - top probability ranks contested vs clear items with AUROC 0.744 (exploratory secondary S1). The signal exists; the scale is wrong.
- One global temperature (T = 11.94) fixes contested items (0.339 to 0.044) and breaks clear ones (0.081 to 0.198).
- Claim correction: the "297 questions ... started at 96%" post misdescribes the source; 297 is the count of contested items in the top confidence bin (mean confidence 0.962, soft agreement 0.505), not a set of 297 questions with 47% agreement. "NLI model worse" refers to BART-MNLI, a supervised in-domain reference with larger errors in both strata, which the preregistration says not to put in the same table as Jev.

## What it claims / describes
**Question.** "When people genuinely disagree about an answer, does the model's confidence go down?" (docs/WRITEUP.md:29). Motivation: TypeSafe describes Jev's outputs as calibrated probabilities, and public tests had mostly used single-label tasks.

**Data.** ChaosNLI (Nie, Zhou and Bansal, EMNLP 2020), SNLI + MNLI subsets, 3,113 items with 100 annotator labels each. alphaNLI excluded (2-way task, entropy not on the same scale) (PREREGISTRATION.md:60-66). Yes, this is the public ChaosNLI dataset itself, not a ChaosNLI-style derivative. Strata: lowest and highest quartile of per-item Shannon entropy of the 100-annotator label distribution, entropy thresholds `q_easy = 0.7357948629753385`, `q_hard = 1.1625318905614013` locked before any Jev call, subsampled to n = 750 per stratum with seed 20260923 (PREREGISTRATION.md:50, :66). Plus 100 frozen paraphrases (50 per stratum, Cursor-generated per changelog commit `6b0c88b`) as a contamination check, excluded from dECE. Sentence text is not in the repo (licence CC BY-NC 4.0); ids, counts and hashes are.

**Queries to Jev** (experiments/exp1_difficulty_calibration.yaml:24-65). One call per item carries:
- a Choice question `relation` with options entailment / neutral / contradiction and criteria such as "entailment: The hypothesis must be true if the premise is true", instructions "Use only the premise and the hypothesis in the state. Do not use any outside knowledge of the dataset this pair came from.";
- three Nouls `noul_entailment`, `noul_neutral`, `noul_contradiction`, normalised to sum to 1 (Amendment 9).
R = 10 repeats per item for Jev (feeds the instability secondaries); local baselines run once. Total raw records 22,400 (results/exp1.json:1028-1029). Which repeat pass feeds the primary ECE: "same rows/pass/items as the ECE endpoint" (results/exp1.json:339), exact pass not stated in the files read.

**Scoring and judging.** No LLM judge. Soft correctness = share of the 100 ChaosNLI annotators who picked the model's argmax label; ECE bin accuracy is the mean of that share. Hard scoring (argmax vs majority label) reported beside it, with the caveat that it "puts label noise in the hard stratum only, which inflates dECE in the direction of the hypothesis" (PREREGISTRATION.md:119-121). Jev's `confidence` field is treated as "sharpness, not a probability of being correct. Metrics refuse to treat it as one" (README.md:66); ECE uses the probabilities.

**Statistics.** Primary endpoint soft top-label dECE = ECE(high-entropy) - ECE(low-entropy), M = 10 uniform bins, stratified two-sample bootstrap (10,000 resamples, BCa and percentile) reported, but primary inference is a parametric bias-corrected test (Amendment 8): estimate E0 = E[ECE | p] per stratum at the observed top probabilities by 2,000 calibrated Beta-Binomial soft draws (kappa = 20), corrected dECE = (ECE_h - E0_h) - (ECE_e - E0_e), two-sided p against the simulated null (PREREGISTRATION.md:379-389). Reason: raw soft null FPR about 0.112, "entirely upper-tail", because easy items pack into few high-p bins; corrected FPR about 0.051. Verdict rule: tracks = corrected >= 0.09 AND p < 0.05; holds = one-sided reject dECE >= 0.09 AND corrected <= 0.02; else inconclusive (PREREGISTRATION.md:89-93). The author notes composite "tracks" power at exactly 0.09 is about 0.5 by construction.

**Preregistration and deviations.** Plan hashed and timestamped with OpenTimestamps (docs/WRITEUP.md:37). Amendments 6 to 11 dated 2026-09-24, each stating "No Jev output observed", bound at commit `ed4655f9`; pilot calls on excluded items started 2026-09-24T04:11:33Z, before some clerical edits (disclosed, docs/PREREG_CHANGELOG.md:11-20). Post-data changes, disclosed: BART client used zero-shot classification on `str(state)` instead of NLI on (premise, hypothesis), re-run as `bart_mnli_nli` with the broken run retained; S3 temperature grid capped at 5.0 with the optimum at the cap, widened to 0.05 to 100 (docs/PREREG_CHANGELOG.md:41-42).

**Baselines.** Local open-weight only (no paid frontier LLMs, "cite jev-frontier-bench"): Qwen2.5-1.5B-Instruct via logprob prefill, GLiClass (knowledgator/gliclass-base-v1.0), a trivial regex-keyword-majority arm, and facebook/bart-large-mnli as a "supervised in-domain reference, not a zero-shot baseline" (Amendment 11, PREREGISTRATION.md:516-524).

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| soft ECE, clear (low-entropy) stratum, Jev Choice | 0.07598666666666667 | n/a | ChaosNLI, n=750, M=10 uniform (results/exp1.json:394) | Zenodo abstract rounds to 0.076 |
| soft ECE, contested (high-entropy) stratum, Jev Choice | 0.3390533333333334 | n/a | n=750 (results/exp1.json:395) | |
| raw soft dECE, Choice | 0.26573333333333327 (corrected-soft block); point 0.26306666666666667 (bootstrap block) | 0.09 tracks threshold | results/exp1.json:89, :399 | two raw values from two computations in the same file; abstract quotes corrected |
| bias-corrected dECE, Choice | 0.2636222846666666, CI 0.24386 to 0.27822, p "p < 1/2001" | null E0 bias 0.0021 | 2,000 null sims, kappa 20 (results/exp1.json:84-97) | verdict "tracks" |
| BCa 95% CI on raw dECE, Choice | [0.24776, 0.28245] | | 10,000 resamples (results/exp1.json:383-386) | |
| mean top-label confidence vs mean soft correctness, clear | 0.91524 vs 0.8443733 (overconfidence 0.0709) | | n=750 (results/exp1.json:215-218) | hard scoring: 0.915 vs 0.925 |
| mean top-label confidence vs mean soft correctness, contested | 0.8068 vs 0.4677467 (overconfidence 0.3391) | | n=750 (results/exp1.json:333-336) | the posts' "81% vs 47%" |
| contested items in 0.9-1.0 confidence bin | count 297, mean_conf 0.9621, soft mean_correct 0.5047 | clear stratum same bin: count 543, 0.9845 vs 0.9011 | results/exp1.json:269-272, :328-331, :152-155 | this is the source of the post's "297 ... 96%" |
| corrected dECE, Jev normalised three-Noul | 0.07633535845071535, CI 0.0597 to 0.0905, p < 1/2001, p_holds 0.0025 | | n=750 per stratum (results/exp1.json:544-557) | verdict "inconclusive"; soft ECE 0.0822 clear, 0.1595 contested |
| hard-scoring dECE, Choice / Noul | 0.2089 (BCa 0.171 to 0.247) / -0.1158 (BCa -0.150 to -0.086) | | results/exp1.json:482-502, :942-962 | hard scoring biased toward H1 by design; Noul hard ECE is lower on contested than clear |
| M-bin robustness, Choice | points 0.260 to 0.268 across M in {5,10,15,20}, uniform and quantile, all CIs exclude 0 | | results/exp1.json:403-479 | "conclusion_flips_with_M": false |
| JSD to human distribution, Choice | clear 0.0563, contested 0.1756 | uniform guess: clear 0.3043, contested 0.0701 | results/exp1.json:341-366 | on contested items a uniform guess is closer to humans than Jev Choice (inference from these numbers); Noul contested 0.0682 |
| AUROC of 1 - top probability, contested vs clear | 0.7438151111111111 (bootstrap CI 0.7187 to 0.7681) | cross-primitive JSD 0.523, flip rate 0.522, mean pairwise TVD over 10 repeats 0.747 | exploratory S1, 10,000 boot, seed 20260924 (results/exp1_s1.json:260-299) | Spearman vs entropy rho 0.477 |
| temperature scaling S3 | mean T 11.94010970920856; soft ECE clear 0.0812 to 0.1983, contested 0.3391 to 0.0437 | | stratified half fit, half evaluate, swapped (results/exp1_s3.json:7-17, :81) | grid widened post-data |
| BART-large-MNLI (fixed client), soft ECE clear / contested | 0.1444 / 0.4320; corrected dECE 0.2857 (CI 0.262 to 0.308), verdict tracks | | results/exp1_bart_fix.json:13, :319-320, :455 | supervised in-domain reference; accuracy vs majority 0.697; AUROC(1 - top) 0.693 (line 2291) |
| local baselines corrected dECE | Qwen2.5-1.5B 0.0997 (tracks); GLiClass -0.0473 (holds); trivial 0.0091 (holds); broken BART 0.0719 | | results/exp1_baselines.json:9, :469, :929, :1389, verdicts :451-1831 | weak arms: paraphrase-original accuracy 0.31 Qwen, 0.39 GLiClass, 0.48 trivial |
| contamination check, accuracy original vs paraphrase | Jev 0.79 vs 0.74 (drop 0.05) | BART 0.39 vs 0.31; Qwen 0.31 vs 0.21 | n=100 frozen paraphrases (results/exp1.json:14-58) | SNLI public since 2015, MNLI since 2018; directional, not dispositive |
| cost | TypeSafe provided $5 of API credit; total spend about $0.41 | EXP-1 hard cap $1.00 | docs/WRITEUP.md:75; PREREGISTRATION.md:492-498 | |
| bias-correction validation | naive comparison flagged 1 in 10 perfectly calibrated models; corrected FPR 0.051 | | 100 simulated calibrated models (docs/WRITEUP.md:39) | simulator assumes Beta-Binomial annotator sampling |

## Mechanism details you could implement
- **Stratify your calibration check by disagreement, not just overall.** Collect multiple labels per decision (ChaosNLI used 100; we could use 3 to 5 reviewers), compute per-item label entropy, split into low and high entropy strata with equal n, and compare ECE between them. Report bin occupancy with every ECE.
- **Soft correctness** = share of labellers agreeing with the model's argmax. This avoids the "hard stratum gets all the label noise" bias of majority-vote scoring.
- **Bias-correct binned ECE comparisons.** At the observed probabilities, simulate a perfectly calibrated model (Beta-Binomial draws of labeller shares), compute E0 per stratum, subtract. Without this, the naive comparison had about 2x the nominal false-positive rate, all in the direction of "worse on hard".
- **Use Jev probability as a ranking signal for contestedness** (AUROC 0.744 here): e.g. route items with low top probability to review or abstain, rather than treating p as the chance of being right. Repeat-instability (mean pairwise TVD over 10 repeats, AUROC 0.747) performed about the same at 10x the calls.
- **Ask the question both ways** when cost allows: a Choice question plus one Noul per option in the same call; the normalised Nouls were better calibrated on contested items in this study (corrected dECE 0.076 vs 0.264). Jev Choice question template used (yaml:24-35): `kind: choice`, three criteria, plus an instruction to use only the state.
- **Do not fit one global temperature**; if you recalibrate, fit per stratum or with a disagreement-aware method (inference from S3 result).
- The harness itself: pinned model, JSONL of every response, offline metrics, preregistration lock file with SHA-256 of item and label files; a scored run refuses to start if hashes change (README.md:49).

## Limitations, caveats, counter-evidence
- Author-stated: "One task (natural language inference), one dataset (ChaosNLI), one model version (jev-1.13.0). Newer versions might behave differently. This measures agreement with people, not some deeper truth. The Noul result is inconclusive." (docs/WRITEUP.md:71)
- The posts give only the Choice arm. The Noul arm, from the same call, is inconclusive at 0.076 and just under the 0.09 threshold; a builder reading the posts would overestimate how badly Jev behaves if they use Nouls (inference).
- AUROC 0.744 is an exploratory secondary (Amendment 10 S1), not a preregistered primary endpoint.
- BART-MNLI "worse" is not a like-for-like comparison: it is fine-tuned on MNLI and ChaosNLI-MNLI items come from MNLI's development set; the preregistration says "Do not put BART in the same comparison table as Jev" (PREREGISTRATION.md:516-521). The first BART run had a client bug fixed after data were seen.
- Contamination: SNLI/MNLI have been public for years; Jev lost 5 points of accuracy on 100 paraphrases. Calibration on contested items could still be affected by memorised labels (inference).
- Soft correctness treats the 100-annotator share as ground truth; ChaosNLI's high-entropy items include genuinely ambiguous and badly written pairs.
- Timing: some clerical prereg edits followed pilot calls (on excluded items), and the amendments carry labels such as "PROMPT P", "PROMPT Q", suggesting AI-assisted drafting (inference); paraphrases were generated with Cursor. All disclosed.
- The PDF text could not be extracted by the fetch tool; I relied on the Zenodo abstract, the committed result JSONs at the pinned commit and the author's write-up. Figure-only content in the PDF (reliability diagrams) was not read.
- Vendor relation: TypeSafe supplied $5 of credit and received the paper before publication (docs/WRITEUP.md:75). The author credits nine earlier community Jev benches (README.md:122-132), including MohitSV/jev-calibration-audit and manjunathshiva/jev-frontier-bench, which already looked at ChaosNLI; this study claims to be the first preregistered, equal-n, bias-corrected stratified test, not the first look.
- Counter-evidence from the author's own related-work log: jev-frontier-bench reports on 50 ChaosNLI ambiguity items JSD to the human split "Claude Fable 5.1 0.043, MiniMax 0.107, Jev 0.149; uniform 1/3 baseline 0.127 (beats Jev)" (paper/RELATED_WORK.md:80), consistent in direction with this study.
- No instruction-bearing content aimed at AI agents was found in the Zenodo record, README, write-up, preregistration or repo markdown.

## Takeaways for tuning a memory stack
- Do not use raw Jev Choice probabilities as "act if p >= 0.9" on inputs where reviewers would disagree. In this study, contested items in the 0.9 to 1.0 bin were right (by annotator share) only about 50% of the time.
- Fit gate thresholds locally on our own labelled decisions (supports B14), and evaluate specifically on the borderline or contested population (supports B13): overall ECE hides the problem because clear items dominate.
- For write-gate and supersession questions that are inherently contested (is this a decision? does this reverse the old requirement?), prefer Noul per-option questions or add an abstain/route-to-review band keyed on low top probability.
- Use Jev's top probability as a contestedness score for routing (AUROC 0.744), not as a correctness probability.
- If we recalibrate, do not use one global temperature; stratify.
- Collect multi-reviewer labels (at least a subset) for our PDLC gate benchmark so we can measure disagreement-conditional calibration, which single-label sets cannot.

## Open questions
- Does the same pattern hold for newer Jev versions (after 1.13.0) and for the Noul-based questions our gates actually use?
- Does it hold for structured PDLC decisions (write gate, supersession, staleness) where "disagreement" comes from ambiguous artifacts rather than ambiguous sentence pairs?
- What is the calibration of open-weight System One models (Laya, Intern-Decision) under the same protocol? The harness supports adding clients.
- Which repeat pass (of 10) feeds the primary ECE, and would averaging the 10 repeats improve calibration on contested items? Not stated in files read.
- How many labellers per item do we need for the soft-correctness estimate to be usable (ChaosNLI used 100)?

## Grading and labels
- **Directness:** high. Tests the exact vendor claim (calibrated probabilities) on the population where it matters for gates (contested inputs).
- **Control:** high. Preregistered with hashes and timestamp, equal n, parametric bias correction validated by simulation, robustness sweep, two arms from the same call; two post-data fixes disclosed (BART client, temperature grid) and neither touches the Jev primary.
- **Independence:** high. Independent author, public human labels, no LLM judge, no shared model between system and judge. Minor: vendor-provided $5 credit; author also publicises his own work in the posts.
- **Reproducibility:** medium. Pinned commit, locked ids, per-bin JSON; raw Jev responses and text not committed; needs a TypeSafe key and the pinned model version.
- **Applicability:** medium. One NLI task; mechanism (confidence not dropping with human disagreement) is plausible for our gates but not shown on PDLC artifacts.
- **Pillars:** R9 primary (Jev as a System One model at memory gates), R4 (calibration, abstention thresholds) and R6 (preregistration, bias-corrected ECE) secondary.
- **Stage:** none (applies to every stage that thresholds Jev probabilities: write_gate, linking, recall_gate, staleness).
- **Tags:** mechanism calibration, confidence-thresholding, temperature-scaling, choice-vs-noul-primitive, ambiguity-detection; workload nli, chaosnli, human-label-variation; cross-cutting preregistration, bias-corrected-ece, vendor-claim-audit, independent-replication.
- **Beliefs supports:** B14 (vendor calibration is claimed, not shown: here it is shown to fail on contested inputs, while holding on clear ones); B13 (evaluate on the borderline population: aggregate calibration looks fine, contested stratum does not).
- **Beliefs contradicts:** none.
- **Would create:** disagreement-conditional overconfidence of Jev Choice (0.076 vs 0.339 soft ECE); Choice vs Noul calibration differ; single temperature cannot fix both strata.
- B21 (rule of three) is not engaged: sample sizes are 750 per stratum and results are intervals, not zero-event bounds.

## Origin chain
- post 2104787761609732582 (@HeyGautamTalks) -> https://zenodo.org/records/22971492 (paper v1.0) -> Zenodo abstract; numbers traced to results/exp1.json at commit dd010299.
- post 2104797306113388591 -> same Zenodo record -> AUROC 0.744 = results/exp1_s1.json:281 (`one_minus_top`); "81% vs 47%" = results/exp1.json:333-336.
- posts 2104787527391482063 and 2104795816925798870 -> YouTube video https://www.youtube.com/watch?v=C6chAhTWvP4 (not watched; same author) -> same numbers as write-up.
- post 2104777143482044927 -> https://github.com/GautamTalksDev/jevbench -> "297" and "96%" = results/exp1.json:269-272 (contested stratum, 0.9-1.0 bin: count 297, mean_conf 0.9621); claim correction above.
- Earlier parked cluster x:2104435470620848342 (no primary source at the time) is resolved by this note.
- Independence notes: all five posts are by the paper's author, so they add no independent evidence. Labels come from ChaosNLI (Nie, Zhou, Bansal 2020), independent of both the author and TypeSafe. No shared harness with TypeSafe; the author acknowledges prior community benches (MohitSV/jev-calibration-audit, manjunathshiva/jev-frontier-bench and others) that also used ChaosNLI, so the dataset is shared with those studies. Not to be confused with JevBench by Florian Standhartinger (Benchmark Heaven leaderboard, notes N-20260928-17 and N-20260929-09), a different project.
