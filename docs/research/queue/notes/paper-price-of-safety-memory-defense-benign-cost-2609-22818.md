---
schema_version: 1
artifact_id: N-SURVEY-20260928-01
artifact_type: note
producer: triage
run_id: survey-20260928T055608Z-7419
created_at: 2026-09-28T06:22:11Z
idempotency_key: note:survey:arxiv:2609.22818
input_refs: []
pillar_primary: R8
pillar_secondary: [R6]
beliefs_affected:
  supports: []
  contradicts: []
  qualifies: [B24]
evidence:
  directness: medium (measures benign-case false quarantine of memory-poisoning defenses; not an injection classifier like jevmem's gate)
  control: high (one variable changed per condition; same backend, retrieval, judge; 3 replicates; bootstrap CIs and McNemar)
  independence: medium (academic authors, no product; judge from a different provider than the agent)
  reproducibility: high (code, per-cell logs and versions.md pins at github.com/pritom02bh/memdefense, MIT)
  applicability: low-medium (LoCoMo chat conversations, not engineering build-time memory; one agent model)
source_url: https://arxiv.org/abs/2609.22818
found_via: survey
---

# The Price of Safety: Benign-Case Utility and Token Overhead of Memory-Poisoning Defenses in LLM Agents

- **URL:** https://arxiv.org/abs/2609.22818 (HTML full text read at https://arxiv.org/html/2609.22818); code https://github.com/pritom02bh/memdefense
- **Type:** paper
- **Author / org:** not stated in the fields read (repo owner pritom02bh)
- **Date:** September 2026 (arXiv 2609.22818v1)
- **Retrieved:** 2026-09-28 (local copy: out/log/h-2609.22818.html)
- **Cited by evidence:** top-down survey, R8 question 1 (benign false-block rate of memory gates)
- **Relevance to a memory stack:** high, it is the only source found that measures what memory-poisoning defenses cost on attack-free traffic, split by where in the pipeline they sit

## TL;DR
- Four defenses tested on purely benign LoCoMo traffic, one variable changed per condition, 3 replicates x 5 conversations.
- Write-time defenses (sanitize, provenance tagging, LLM anomaly check) show no resolvable utility cost and a false quarantine rate (FQR) of 0.000.
- The read-time reranker defense costs -4.4 pp accuracy (95 % CI [-9.0, -0.05], McNemar p = 0.064) and quarantines 33.6 % of legitimate memories it adjudicates, up to 106 false quarantines in one conversation.
- Stacking all four does not compound the cost (-3.1 pp, FQR 0.303).
- Authors' conclusion: where a defense intercepts the pipeline predicts its benign price better than whether it uses an LLM.

## What it claims / describes
Measurement harness holds the memory backend (Mem0-based, per the repo), retrieval (text-embedding-3-small, fixed candidate count and similarity threshold), answer format and judge constant, and changes only the defense. Agent backbone gemini-3.1-flash-lite; judge claude-haiku-4-5-20251001 ("To avoid a model grading its own output, the judge comes from a different provider"). Five LoCoMo conversations up to 150 turns, questions per conversation 75, 51, 32, 42, 55. 6 conditions x 5 conversations x 3 replicates = 90 cells. Pipeline noise was "significant even at temperature zero", which is why replicates are used.

Defenses as described: Sanitization "scans each candidate for patterns common in injection attacks... Any matching pattern is discarded or rewritten prior to storage". Provenance "tags indicate each memory's source and trust level; memories from untrusted or ambiguous origins receive a lower trust weight". Anomaly detection passes "each candidate memory to an LLM to verify its consistency with the ongoing conversation. Inconsistent candidates are quarantined instead of stored". Reranker (read time) "does not modify storage but operates during memory retrieval... Memories that poorly match or contradict others are flagged and isolated in quarantine". Specific thresholds and prompts: not stated in the paper text read; the repo stores prompts (judge prompt in `prompts/judge.txt`).

## Numbers
| Defense | Stage | Utility delta (pp) | 95 % CI | Token overhead | FQR |
|---|---|---|---|---|---|
| No defense | none | 0.000 | n/a | n/a | 0.000 |
| Sanitize | write | +1.8 | [-1.7, +5.6] | 0.0 % | 0.000 |
| Provenance | write | +1.9 | [-2.2, +6.0] | 0.0 % | 0.000 |
| Anomaly (LLM) | write | +3.1 | [-0.9, +7.1] | 1.2 % | 0.000 |
| Rerank | read | -4.4 | [-9.0, -0.05] | 2.7 % | 0.336 |
| Stacked (all four) | write + read | -3.1 | [-7.4, +1.0] | 4.1 % | 0.303 |

Resolution: CIs span roughly +/-4.5 pp, so a real cost of 1 to 2 pp for write-time defenses would be undetectable (authors say so). Text and Table 3 agree (verified against the HTML).

## Mechanism details you could implement
- Measure a gate's false-block rate on attack-free traffic as a first-class metric (FQR = legitimate items quarantined / legitimate items adjudicated), alongside utility delta and token overhead.
- Hold backend, retrieval, judge and answer format fixed; change only the defense; replicate each cell three times because temperature-zero pipelines still vary.
- Judge from a different provider than the agent.

## Limitations, caveats, counter-evidence
- Benign traffic only: no attack-block rate is reported, so a write-time defense with 0 FQR here might also block little (inference). Cost and benefit are in different papers.
- One agent model; calibration and evaluation share a source; act-time interception not evaluated.
- The read-time "reranker" defense is a contradiction/poor-match quarantine, not an injection classifier. It is a different mechanism from the jevmem injection gate behind B24 (inference), so the 33.6 % does not transfer directly; what transfers is that read-time quarantine on conversational memory can have a large false-block rate that attack-only evaluations never show.
- Chat memory (LoCoMo), not engineering-agent memory.

## Takeaways for tuning a memory stack
- B24's evidence (0/22 false blocks) is 22 benign lines; this paper shows false-block behaviour only becomes visible at hundreds of adjudicated items per conversation. H10's requirement of at least 149 independent benign cases is the right order of magnitude, and should be counted per adjudicated item and per conversation.
- Test the gate at both placements (write time and read time) on the same benign set; the stage may matter more than the model.

## Open questions
- Attack-side block rates of the same four defenses in the same harness.
- Whether an injection-specific classifier at read time behaves like the write-time defenses (near-zero FQR) or like the reranker.
