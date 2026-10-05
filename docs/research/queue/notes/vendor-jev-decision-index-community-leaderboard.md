---
schema_version: 1
artifact_id: N-20261002-01
artifact_type: note
producer: triage
run_id: triage-20261002T014502Z-1ef3
created_at: 2026-10-02T01:52:51Z
input_refs: [{"artifact_id": "post:2105104332756754743", "file_id": null, "sha256": null}, {"artifact_id": "post:2105136265549218270", "file_id": null, "sha256": null}, {"artifact_id": "post:2105165764294836461", "file_id": null, "sha256": null}, {"artifact_id": "post:2105185645086003710", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:multimodalart/jev-decision-index
claim_cluster: hf:multimodalart/jev-decision-index
feeds: ["memory", "decision"]
primary_source: https://huggingface.co/spaces/multimodalart/jev-decision-index
source_commit: cdbd1cab3b6eb1811ebd82d2686ad563a4d0fc0d
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R6", "R4"]
memory_stage: evaluation
priority: 2
tags: {"mechanism": ["typed decision model", "chance-corrected index", "reliability diagram"], "workload": ["classification", "retrieval ranking", "tool choice", "NLI"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high, per-benchmark scores, request counts, latency, cost and reliability bins are in the pinned JSON", "control": "medium, frozen 120,340-request corpus with hard rules (no truncation, no option pruning, no prompt tuning, unanswered counts as wrong), but point estimates only and Jev is called over HTTPS while open entrants run on one local card", "independence": "medium, community maintained and not affiliated with TypeSafe, but the build script lives in a 'typesafe-diffusion-lab' checkout and some rows are author-submitted runs adopted after a spot reproduction", "reproducibility": "medium, data bundle pinned at a commit with a corpus sha256, the builder script and request corpus are not in the Space", "applicability": "medium, public classification, NLI, retrieval and tool benchmarks, no engineering-agent memory task and no long structured artifacts"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Jev 1.13 is close to calibrated overall on public decision benchmarks (ECE 0.074) but overconfident on retrieval and classification (confidence 0.82 vs accuracy 0.67), so retrieval-stage thresholds must be fitted locally"]}
claim_correction: Posts say Liquid AI's d1 is the first model to beat Jev on Hugging Face's Decision Index (58.9 vs 57.9); the pinned community index (0.2.1, generated 2026-09-28) confirms Jev at 57.91 but carries no d1 row, and no entrant on it beats Jev (best 57.44), so the d1 score is vendor-reported and unverified; Maincode also vendor-reports MATILDA-jev at 59.26 on 0.2.1 (N-20261001-04), which bears on the 'first' claim
---

# Jev Decision Index 0.2.1 (community leaderboard of Jev and open-weight System One reproductions), as the yardstick behind the Liquid d1 "beats Jev" claim

- **URL:** https://huggingface.co/spaces/multimodalart/jev-decision-index (data: `data/index.json`, `data/methodology.json`)
- **Type:** repo (static Hugging Face Space with a JSON data bundle)
- **Author / org:** multimodalart (Space owner); README: "Unofficial and community-maintained; not affiliated with TypeSafe AI." Data written by `evaluation/reproductions/build_leaderboard.py` "in the `typesafe-diffusion-lab` checkout" (README; that checkout is not public in the Space)
- **Date:** edition "Decision Index 0.2.1", date 2026-09-28 (`methodology.json` `edition`); `index.json` `generated_utc` "2026-09-28T00:39:36+00:00"; Space last modified 2026-10-02T01:22:48Z
- **Retrieved:** 2026-10-02, Space commit `cdbd1cab3b6eb1811ebd82d2686ad563a4d0fc0d` (via the Hub API), files downloaded to `repos/jev-decision-index/` (README.md, data/index.json, data/index-v2.json, data/index-v0.2.1.json, data/methodology.json, data/methodology-v2.json, news.html). Corpus sha256 `b2b56d6fb636837ca469e689087bdbf373dda8de7638aa2da6793e6eda0792d5` (`index.json` `suite.corpus_sha256`).
- **Cited by evidence:** Liquid d1 cluster: @CoderGeeta https://x.com/CoderGeeta/status/2105104332756754743 ("liquid ai's d1 just edged jev on huggingface's decision index, 58.9 to 57.9"), @Secretof_forest https://x.com/Secretof_forest/status/2105136265549218270, @timur000kh https://x.com/timur000kh/status/2105165764294836461 (quoting @liquidai https://x.com/liquidai/status/2105003472332693869), @swordBluesy https://x.com/swordBluesy/status/2105185645086003710 (reply). Trend: decision-trends 2026-09-25 "Jev Decision Index 0.2 subtracts chance-level guessing" and 2026-09-29 "Liquid AI ships d1".
- **Relevance to a memory stack:** medium. It is the only public, frozen, multi-benchmark yardstick that puts TypeSafe Jev, Intern-Decision, Laya, this-that-model, semif, CLM, GLiNER2.5-Decide and others on one table with reliability bins, so it is where vendor "beats Jev" claims should be checked; it contains no memory-stage task.

## TL;DR
- **Claim correction for Liquid d1.** Jev's 57.9 in the d1 posts matches Jev's chance-corrected headline on this index, 0.2.1: `"balanced_skill":57.91` (`index.json` `jev.scores`). But the pinned board (generated 2026-09-28, two days before d1's launch) has **no d1 row**, and **no entrant beats Jev**: the best is Surogate Rune 26B-A4B v3 at 57.44. d1's 58.9 is therefore vendor-reported and not visible on any page we could read; `huggingface.co/spaces/huggingface/decision-index` still returns 401. Whether "Hugging Face's Decision Index" in Liquid's post is this Space is not stated (inference: the Jev number and edition match).
- **Jev calibration, measured by a third party.** Over 32 benchmarks with a right or wrong answer (a 1-in-6 request sample, n = 72,594): accuracy 0.7393, mean confidence 0.8115, ECE 0.074, Brier 0.3558. Overconfidence is concentrated in the **retrieval and classification** area: confidence 0.8206 vs accuracy 0.6685, ECE 0.1536. Tools is nearly calibrated (0.9534 vs 0.9458, ECE 0.0196).
- **Open-weight gap is large on this panel.** Of 70 entrants, the strongest open models are 26B to 31B (57.44, 57.33, 56.4). At about 4.7B served parameters: Decider 4B 40.7, Intern-Decision-4B 37.81, kev-4b 34.64, semif 25.94; GLiNER2.5-Decide 11.21; Laya 6.04; CLM-v0.1-8B 7.4. Intern-Decision-4B is the best calibrated of the small ones (ECE 0.0278).
- **Method is strict and documented:** no truncation, no option pruning, no prompt tuning, unanswered counts as wrong, each benchmark chance-corrected to (score - chance) / (1 - chance). Point estimates only, "no uncertainty intervals yet".
- **Latency is not comparable across rows:** Jev is the hosted API over HTTPS (median 524.1 ms on the latency sample), open entrants are timed on one RTX PRO 6000 excluding network.

## What it claims / describes
A static leaderboard ("Jev Reproductions Tracker", README) of "every open reproduction that finished the frozen suite, scored with one number, the Decision Index, plus per-category radars against Jev". The Space serves edition 0.2.1 (`suite.label` "Decision Index 0.2.1", `panel_id` "decision-index-0.2.1", `jev_version` "jev-1.13.0").

**Corpus and gate.** `suite.requests` 120,340, `scoreable` 119,898, 43 benchmarks, 38 in the index panel, 5 areas. "A run enters the index only when its status event is \"complete\" and it has processed at least 119,898 rows (the 120,340-request corpus minus the 442 questions excluded for every engine)" (`methodology.json` `rules.complete_run_gate`). Hardware: "1 x NVIDIA RTX PRO 6000". Six interactive environments (MiniWoB++, Boxoban, RTFM, ScienceWorld, Hanabi, Codenames) are dropped for everyone because "no reproduction has run them".

**Areas and weights (0.2.1, `suite.index_note`).** "Arts & Human Taste weighs 10%; the other four share 90% in proportion to the square root of their benchmark count (knowledge 25.8%, language 25.8%, retrieval 20.0%, tools 18.3%). Inside an area, gold ★ benchmarks weigh 1.2 and the rest 1.0." Gold: MMLU-Pro, BBH, GPQA Diamond, HLE, ANLI, WinoGrande, HellaSwag, BANKING77, CLINC150, BRIGHT, BFCL, API-Bank, ForecastBench.
- knowledge: GPQA Diamond, GSM8K, ChessBench, MuSR, SATA-Bench, CRUXEval, CLadder, HLE, MMLU-Pro, BBH
- language: ContractNLI, ANLI, WinoGrande, HellaSwag, ACOS, FinEntity, iSarcasmEval, VAST, NLI4CT, RAGTruth
- retrieval: BANKING77, CLINC150, BRIGHT, Amazon ESCI, PhishNChips, HoVer
- tools: BFCL, ToolRet, API-Bank, Home appliances, When2Call
- arts: BPoMP, Humicroedit, POP909, cfcolor, ForecastBench, Habermas, New Yorker
- Outside the index but shown: RouterBench ("the prompt reveals that GPT-4 is the best route"), SGD ("build bug, pending re-run"), MMLU, ARC-Easy, ARC-Challenge.

**Headline.** `suite.headline` = `balanced_skill`: each benchmark mapped to (score - chance) / (1 - chance), clipped to 0 to 1, "so 0 means random guessing and 100 means perfect"; "Every score is coverage-adjusted, so an unanswered or unsupported request counts as wrong." ForecastBench: "clip((0.25 - Brier) / 0.25) x coverage". Chance levels are per benchmark (for example RAGTruth chance is "always answering \"hallucinated\" (F1 0.518)", ToolRet and BRIGHT use expected nDCG@10 of a random ranking over answerable queries only, "685 of 1,000 and 220 of 550").

**Hard rules (`methodology.json` `rules.hard_rules`, verbatim names):** "No truncation" ("A model whose context window cannot hold a prompt records that request as unsupported; it is never shortened to fit"), "No label filtering", "No prompt tuning", "No labels in the adapter", "No correctness-based retry" ("Transient transport errors retry up to twice"), "Native abstentions stand", "Unanswered = wrong".

**Calibration readout (`suite.calibration_note`).** "32 benchmarks with a per-field right or wrong answer (ToolRet, BRIGHT, RouterBench and ForecastBench excluded), each weighted equally; a 1-in-6 sample of requests; confidence is the probability placed on the chosen option. Rows an entrant trained on count as wrong here too."

**Author-submitted rows.** 0.2.1 changes include rows adopted from authors after a spot check, for example "Surogate Rune 26B-A4B v3 replaces v1 on the board: the author's submitted run, adopted after our 3,000-row reproduction matched it exactly."

## Numbers

| metric | value | baseline | setup/benchmark (n) | caveat |
|---|---|---|---|---|
| Jev 1.13.0 Decision Index 0.2.1 (balanced_skill) | 57.91 | chance = 0 | 38 benchmarks, ~120k requests (`jev.scores`) | point estimate, no interval |
| Jev balanced_raw / breadth_skill | 68.09 / 57.08 | | same | |
| Jev area skill: knowledge / language / retrieval / tools / arts | 0.514 / 0.6202 / 0.5542 / 0.7509 / 0.3766 | | `jev.categories` | post says d1 "loses tools by a point"; unverifiable |
| Liquid d1 vs Jev (from posts) | 58.9 vs 57.9 | | not on the pinned board | vendor-reported; claim correction |
| best non-Jev entrant on board | 57.44 (Surogate Rune 26B-A4B v3) | Jev 57.91 | 70 entrants | no entrant above Jev at this commit |
| next: Decider chat Gemma-4-31B / pplx-decider-v1-27b | 57.33 / 56.4 | | | |
| Jev calibration overall | acc 0.7393, conf 0.8115, ECE 0.074, Brier 0.3558, share of answers with conf > 0.95 = 0.0207 (`over95`) | | n = 72,594, 32 benchmarks (`jev.calibration`) | 1-in-6 request sample |
| Jev top reliability bin (conf >= 0.9) | conf 0.9808, acc 0.9342, weight 0.5388 | | same | about 4.7 points overconfident on over half the answers |
| Jev bin 0.7 to 0.8 | conf 0.7465, acc 0.5904 | | same | 15.6 points overconfident |
| Jev calibration, retrieval area | acc 0.6685, conf 0.8206, ECE 0.1536 | | BANKING77, CLINC150, Amazon ESCI, PhishNChips, HoVer (BRIGHT excluded) | the memory-relevant area is the worst calibrated |
| Jev calibration, tools / language / knowledge / arts | ECE 0.0196 / 0.0617 / 0.0654 / 0.0934 | | | |
| Jev BRIGHT nDCG@10 | 0.4752 | chance 0.116 | 220 answerable queries; median 405.7 ms, p95 637.5 ms, $0.137 | |
| Jev ToolRet nDCG@10 | 0.6528 | chance 0.1341 | 685 queries; median 319.2 ms; $0.274 | |
| Jev BANKING77 / CLINC150 macro-F1 | 0.7974 / 0.8927 | | 3,080 / 5,500 cases; $0.222 / $0.644 | |
| Jev RAGTruth F1 (hallucinated class) | 0.7653 | 0.518 always "hallucinated" | 2,700 cases; median 1,039.7 ms | added in 0.2 |
| Jev HoVer accuracy | 0.7285 | 0.5 | 4,000 cases | added in 0.2 |
| Jev BFCL case exact accuracy | 0.9575 | 0.2592 | 1,694 cases; median 265.7 ms | |
| Jev hosted latency on latency sample | median 524.1 ms, p95 536.0 ms | | "one sequential HTTPS client" (`jev.latency.note`) | "Not comparable to the on-card single-process figures"; "Its answers on this sample differ from the Sep-19 board rows in 20 choices: API output drifted" |
| Jev summed USD across 48 result rows with a cost field | 7.837 USD for 141,267 cases | | my sum of `usd` and `cases` fields (inference) | includes non-index rows |
| Intern-Decision 0.8B / 2B / 4B | 11.94 / 19.38 / 37.81; ECE 0.0255 / 0.0608 / 0.0278 | Jev 57.91, ECE 0.074 | same corpus, local card | open weights |
| Decider 4B / kev-4b-raised / semif | 40.7 / 34.64 / 25.94; ECE 0.0837 / 0.1756 / 0.0989 | | ~4.66B served params each | |
| this-that-1.2 / GLiNER2.5-Decide / Laya (1e28ac20) / CLM-v0.1-8B | 28.14 / 11.21 / 6.04 / 7.4 | | | Laya ECE 0.1402, GLiNER2.5-Decide ECE 0.0884 |
| LFM2.5-2.6B-RLCD (community, on Liquid base) / LFM 350M | 6.76 / 1.38 | | `lfm2600`, `lfm350-sdpa` | not Liquid's d1; a third party's decoding on Liquid base weights |
| lowest ECE values on the board | 0.014, 0.0149, 0.0178, 0.0209, 0.0226 | | | entrants not identified in this read |

## Mechanism details you could implement
- **Chance-corrected scoring per benchmark** before averaging: `skill = clip((score - chance) / (1 - chance), 0, 1)`, with chance defined per task (uniform choice, F1 of random guessing over the label set, or the trivial "always positive" F1 when that beats a coin). Use the same rule for our own decision tasks so a model that always says "relevant" does not look good on a skewed set.
- **Coverage-adjusted scores:** unsupported, refused or errored requests score zero against the full denominator ("Nobody climbs by skipping the hard cases"). For a memory gate this is the right accounting for abstentions that are not routed to a fallback.
- **Reliability readout format** worth copying: 10 bins of chosen-option probability, each with weight, mean confidence and accuracy, plus ECE, Brier and `over95` per area (`jev.calibration.rel`, `.areas`).
- **Frozen-corpus discipline:** a sha256 of the request corpus, a complete-run gate (all 119,898 scoreable rows), and a "superseded" policy (one row per model at the configuration that stands).
- **Area weighting:** fixed weight for a taste area and sqrt-of-count weights for the rest, with 1.2 weight for "gold" benchmarks. Any single Index number therefore embeds editorial weights; compare area rows, not the headline, when choosing a model for one memory stage (inference).

## Limitations, caveats, counter-evidence
- **d1 is not on the board.** The d1 claim (58.9) cannot be verified from this source; the "first to beat Jev" claim is also in tension with Maincode's vendor-reported 59.26 for MATILDA-jev on 0.2.1 (bus note N-20261001-04); neither appears on this commit's board.
- **Not independent of TypeSafe tooling in an obvious way:** the build script runs from a `typesafe-diffusion-lab` checkout (README); the README disclaims affiliation. Who runs that checkout is not stated.
- **Jev's rows were run over the hosted API** ("Full release v1" edition of Jev, `jev-1.13.0`); the API "output drifted since the board run" in 20 choices on the latency sample, so Jev's score is a snapshot of a moving service.
- **Point estimates only:** "Point estimates only, no uncertainty intervals yet." A 0.47-point gap (57.91 vs 57.44) or a 1.0-point gap (claimed d1) is not shown to be meaningful.
- **Author-submitted runs** are adopted after partial reproduction (for example a 3,000-row reproduction for Rune v3).
- **Contamination:** "Rows an entrant trained on count as wrong here too" is stated for calibration; whether open entrants trained on public benchmark splits used here is otherwise not stated.
- **No memory task:** nothing on deciding what to store, linking, supersession or staleness; BRIGHT and ToolRet are the closest to our retrieval stage. Applicability to engineering-agent memory is by analogy only (inference).
- The editorial area weights changed between 0.2 and 0.2.1 (`suite.changes`), and Jev's 0.2 score was 51.67 (`index-v2.json`), so any "beats Jev" claim must name the edition.

## Takeaways for tuning a memory stack
- When a vendor says "beats Jev", ask for the edition and the area rows; on 0.2.1 Jev's headline is 57.91 and the board shows nobody above it as of 2026-09-28.
- Do not use Jev's raw probabilities as retrieval or rerank thresholds without local fitting: on this panel its retrieval-area confidence exceeds accuracy by about 15 points (0.8206 vs 0.6685), and the 0.7 to 0.8 bin is right only 59% of the time. A threshold like "auto-accept above 0.9" behaves differently per stage.
- For a self-hosted System One model at a memory stage (priority 2), the realistic open candidates at about 4 to 5B are Decider 4B (40.7) and Intern-Decision-4B (37.81, ECE 0.0278); the 26B to 31B entrants approach Jev. Laya and GLiNER2.5-Decide are far behind on this general panel, which says nothing about a fine-tuned narrow task (see the parked GLiNER2.5-Decide fine-tune report).
- Copy the scoring rules (chance correction, coverage adjustment, reliability bins) into our PDLC memory benchmark scoping (priority 4).

## Open questions
- Is `huggingface/decision-index` (401) the same index, a fork, or an official HF edition? Which edition and corpus hash does Liquid's 58.9 use?
- Will d1 and MATILDA-jev be run by the maintainer on the frozen corpus, and with what calibration?
- Which entrants own the lowest ECE values (0.014 to 0.0226), and do they hold up at the retrieval area?
- Is the `typesafe-diffusion-lab` builder and the request corpus available for a local rerun on our own decisions?

## Grading and labels
- **Directness: high.** Per-benchmark scores, cases, latency, cost and reliability bins are in the pinned JSON.
- **Control: medium.** Frozen corpus with strict rules and a complete-run gate; but no intervals, Jev via HTTPS vs open models on a local card, editorial weights.
- **Independence: medium.** Community maintained, not affiliated with TypeSafe by its own statement; builder runs from a TypeSafe-named checkout; some rows author-submitted.
- **Reproducibility: medium.** Space commit and corpus hash pinned; builder script and corpus not in the Space.
- **Applicability: medium.** Public decision tasks close to routing, reranking and classification; no memory-lifecycle task.
- **Strength:** repo-pinned. **Pillars:** R9 primary (which System One model, hosted vs open weight), R6 secondary (evaluation integrity of "beats Jev" claims), R4 secondary (calibration). **Memory stage:** evaluation. **Priority:** 2 (also bears on 1 and 4).
- **Beliefs:** supports B14 (vendor calibration claimed, not shown: a third-party reliability table shows overconfidence in the retrieval area, so fit thresholds locally); would create a belief that Jev 1.13 is near-calibrated overall but overconfident on retrieval and classification. No contradiction with a held belief.
- **Contradiction rows:** none with the register. Claim contradiction with the Liquid d1 posts (vendor score not on the pinned board; "first" claim in tension with MATILDA-jev's vendor-reported 59.26).

## Origin chain
- Posts (Liquid d1 cluster, 2026-09-30): 2105104332756754743 (58.9 vs 57.9, area wins and losses), 2105136265549218270 ("vendor-reported ... Hugging Face's Decision Index"), 2105165764294836461 (quotes @liquidai's announcement 2105003472332693869), 2105185645086003710 (reply).
- Liquid's docs page `docs.liquid.ai/lfm/models/decision-models` read 2026-10-02: API shape only (Noul, Choice, Score; `"output_tokens": 0`), no benchmark numbers, weights or licence.
- Index: `huggingface.co/spaces/huggingface/decision-index` 401; Hub search found `multimodalart/jev-decision-index`; files read at commit `cdbd1cab3b6eb1811ebd82d2686ad563a4d0fc0d`: `data/index.json` (`suite`, `jev.scores`, `jev.categories`, `jev.calibration`, `jev.results`, `models[]`), `data/methodology.json` (`edition`, `rules`), README.
- Independence: Jev's rows come from TypeSafe's hosted API; the board's maintainer and the builder checkout are not TypeSafe-affiliated by statement; Liquid's d1 claim shares no evidence with the board at this commit. MATILDA-jev's 59.26 (N-20261001-04) is Maincode's own report.
