---
schema_version: 1
artifact_id: N-20260929-16
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104583094078525629", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.27287
claim_cluster: arxiv:2609.27287
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.27287
source_commit: n/a
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R2", "R4", "R8"]
memory_stage: write_gate
tags: {"mechanism": ["outcome-supervised-reflection", "propose-verify", "deterministic-verifier", "wilson-bound-admission", "rule-retirement", "maturation-wall", "rejection-inference"], "workload": ["payment-fraud", "streaming-classification"], "lifecycle_stage": ["admission", "retirement", "learning-from-outcomes"], "cross_cutting": ["verbal-reflection-drift", "entity-bootstrap-ci", "proprietary-data", "human-review-checkpoint"]}
evidence_grade: {"directness": "medium: directly tests a write gate for outcome-learned rules (verified admission vs unverified free-text reflection) but in payment fraud, not engineering-agent memory", "control": "high: chronological replay with an enforced two-cycle maturation wall, matched decision agent and cadence across arms, entity-clustered bootstrap CIs (B=2000), static-state control, proposer ablation, history-shuffle control, backbone matrix", "independence": "low: Coinbase authors on proprietary Coinbase data; ground truth is matured chargeback/investigation labels, not an LLM judge", "reproducibility": "low: data cannot be released, no code link found; prompts, thresholds and protocol are published", "applicability": "low-medium: domain differs; the admission rule (LLM proposes, verifier with confidence bound on matured outcomes admits) transfers to lessons learned from engineering-agent failures (inference)"}
beliefs_affected: {"supports": ["B25", "B18"], "contradicts": [], "would_create": ["Outcome-learned memory entries should enter the active policy only through a deterministic verifier with a lower confidence bound on matured outcomes and a per-cycle admission cap; unverified free-text reflection on the same evidence moved the block rate from a 5% target to 14.8%-41.4% and lowered precision by 13.3 to 25.1 pp"]}
claim_correction: none (roundup's "verifier-gated knowledge admission from matured errors" matches the paper; note the domain is payment fraud and the reported gains are over a frozen LLM decision agent and static CatBoost, while against periodically retrained CatBoost precision and F1 differences are not significant).
---

# SR-Fraud: An Outcome-Supervised Reflective LLM Agent Framework for Non-Stationary Payment Fraud Detection

- **URL:** https://arxiv.org/abs/2609.27287
- **Type:** paper
- **Author / org:** Xuwei Tan (Coinbase, Inc. internship; The Ohio State University), Yao Ma (Coinbase, Inc.), Xueru Zhang (The Ohio State University). Footnote: personal opinions, not Coinbase policy.
- **Date:** v1 submitted 23 Sep 2026 (arXiv stamp, cs.LG)
- **Retrieved:** 2026-09-29 (version v1; full PDF read locally at repos/2609.27287.pdf, 19 pages including appendices A to E)
- **Cited by evidence:** https://x.com/RubberDucky_AI/status/2104583094078525629 (@RubberDucky_AI machine-generated roundup; "verifier-gated knowledge admission from matured errors")
- **Relevance to a memory stack:** medium. The cleanest controlled comparison we have of verified vs unverified learned memory: the same weekly outcome evidence fed either into a free-text reflection memory (Reflexion) or into LLM-proposed rules admitted only by a deterministic verifier with Wilson bounds. The unverified arm drifts the operating point badly.

## TL;DR
- Architecture: a frozen, stateless LLM decision agent assigns risk 1 to 5 per transaction from a Hybrid Episodic Window (last up to 15 transactions + velocity summary); an "Evolving Expert Knowledge State" K = (S, E_rel) edits only boundary cases (escalate some r=3 to block, release some r=4 to allow). K is updated once per weekly cycle offline.
- Update: an offline reflection LLM proposes a hypothesis space (amount atoms, qualifier atoms, release bands); a deterministic harness enumerates conjunctions, verifies against matured labels, and admits at most 5 escalation signatures per cycle ranked by one-sided Wilson lower bound; rules retire when their Wilson upper bound falls below the operating floor.
- Result on 16,140 transactions over 9 weeks (5.04% fraud, case-control sample): full SR-Fraud with Sonnet 4.6 vs the same decision agent without reflection: +5.4 precision, +7.3 recall, +6.2 F1 [3.6, 9.0], +19.3 dollar-weighted recall [14.3, 24.5] at block rate 5.97% -> 6.08% (Section 3.4.1, Table 7).
- Unverified free-text reflection (Reflexion, same cadence and evidence) at risk >= 4: block rates 14.80% (Sonnet), 32.24% (Opus), 41.44% (GPT-5.4) vs 5% target; precision -13.3 / -22.2 / -25.1 vs static CatBoost (Table 2, Table 11).
- Against periodically retrained CatBoost, precision and F1 differences are not significant on the full benchmark; recall (+8.1 [1.7, 14.4]) and dollar recall (+7.8 [0.6, 15.2]) are (Table 7).

## What it claims / describes

**Request path (Section 2.2).** Decision context c_t = Phi(x_t, W_u(t)), W_u(t) = (R_u(t), V_u(t)): bounded time-ordered window of the user's prior transactions (payment rail, amount, destination; no PII) plus a burst-and-velocity summary (inter-arrival min/median minutes, counts in last 10 and 30 minutes, unique-set diversities, historical amounts; Appendix B.2). The LLM outputs exactly one line `RISK_LEVEL: <1-5>`; the parser takes the first `RISK_LEVEL:\s*([1-5])` match; no match is treated as allow "so a malformed generation cannot silently raise the block rate" (Appendix B.3). Block if r >= 4. One LLM call per reviewed transaction; single pass, no thinking, temperature 0.3 (Appendix C.3).

**Knowledge state (Section 2.3, Eq. 3).** esc(x) = [r(x)=3] AND OR_{s in S} s(x); rel(x) = [r(x)=4] AND E_rel(x); block(x) = ([r(x)>=4] OR esc(x)) AND NOT rel(x). Each s is a conjunction over the leaf-feature vocabulary. Empty state K_empty exactly reproduces the decision agent. The LLM policy itself is never rewritten.

**Reflection cycle (Algorithm 1).** For cycle j with matured data D_{<=j-2}: digest -> reflection agent proposes G_j = (A_j amount atoms, Q_j qualifier atoms, L_j release bands) in strict JSON (rationale kept for audit, "never executed") -> harness enumerates H_j = {a AND q1 [AND q2]} -> verify -> select release -> retire -> admit best -> deploy K_j. Selective labels: missed fraud is observable from allowed transactions; false blocks censor their own outcomes, so release safety is estimated by rejection inference on the observable r=3 bank (validated against an oracle in Appendix D.7).

**Admission rule (Eq. 4, Appendix B.1).** LCB_Wil(p_marg(h)) > gamma * p_op and UCB_Wil(p_free(b)) < p_op, one-sided Wilson z = 1.0, gamma = 1.15. Pre-test rarity ceiling rho = 0.020 of legitimate traffic; conditional-precision floor 0.30 on train-validation with at least 10 matched frauds. Escalation needs at least 8 marginal rows and 2 new true positives; per-cycle corroboration: a cycle votes after 2 matched boundary rows, candidate needs at least 2 voting cycles. Retirement: at least 8 marginal rows, Wilson upper bound below the operating floor, and failure of the original train-validation gate. Release band: 20 settled boundary rows, at most one dissenting cycle, exercised by settled data on at least half its proposed ceiling. Up to 5 escalation signatures admitted per cycle, ordered by Wilson lower bound.

**Reflexion baseline (Appendix C.2.4).** Same weekly cadence and maturation wall, same evidence (confirmed false negatives, risk-3 boundary traffic, the week's highest-dollar confirmed fraud); a single running free-text document rewritten weekly and placed directly into the next week's prompt. "The deliberate contrast variable is verification." The authors used "the least-guarded reflection prompt".

## Numbers

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| SR-Fraud (Sonnet 4.6) dP / dR / dF1 / dRecall$ | +4.5 / +12.3 / +8.0 / +11.7, block 6.08% | static CatBoost at 5.00% block (0.0) | Table 2; 16,140 tx, 813 fraud, 9 weekly cycles | pp differences; case-control sample, precision not production precision |
| same, Opus 4.5 / GPT-5.4 | +6.2 / +3.0 / +4.6 / -2.2 (4.59%); -1.2 / +7.6 / +2.7 / +2.8 (6.44%) | static CatBoost | Table 2 | backbone-dependent |
| decision agent only (Sonnet 4.6) | -0.9 / +5.0 / +1.8 / -7.6, block 5.97% | static CatBoost | Table 2 | |
| SR-Fraud minus decision agent (all) | +5.4 [2.8, 8.1] / +7.3 [4.0, 10.7] / +6.2 [3.6, 9.0] / +19.3 [14.3, 24.5] | decision agent, K empty | Table 7, entity-clustered bootstrap B=2000, 95% CI | within >=1, >=2, >=3 prior cohorts P/R/F1 CIs include zero |
| SR-Fraud minus CatBoost-periodical (all) | +0.3 [-4.7, 5.1] / +8.1 [1.7, 14.4] / +3.8 [-1.5, 8.8] / +7.8 [0.6, 15.2] | monthly retrained CatBoost | Table 7 | precision and F1 not significant |
| Reflexion at risk >= 4, Sonnet / Opus / GPT-5.4 | dP -13.3 / -22.2 / -25.1; dF1 -3.9 / -14.8 / -19.6; block 14.80% / 32.24% / 41.44% | static CatBoost 5.00% | Table 2, Table 11 | at risk >= 5: Sonnet +7.0 / +1.8 / +4.2 / -6.6 at 4.34%; Opus 3.79% F1 -13.6; GPT 12.06% F1 -18.8 |
| common block count 6.08% | SR-Fraud vs CatBoost: +6.8 [2.1, 11.5] P, +8.2 [1.3, 14.6] R, +7.5 [2.1, 12.7] F1, +7.3 [-1.1, 15.2] R$ | CatBoost ranked to 982 blocks | Table 12, Appendix D.5 | vs CatBoost-periodical: +3.1 [-1.8, 7.6], +3.7 [-2.8, 10.4], +3.3 [-1.8, 8.4], +1.9 [-5.4, 9.1], none significant |
| online reflection vs static pre-replay state | dRecall$ +4.3 (Sonnet), +11.2 (Opus), +5.9 (GPT) | same system with K frozen at pre-replay | Table 18 | dF1 +0.4 / +2.4 / +1.7 |
| proposer ablation (Sonnet decision agent) | LLM proposer dF1 +8.0, dR$ +11.7 | FP-Growth +4.8 / +4.3; RIPPER +4.3 / +2.1; WRAcc +5.4 / +9.6 (agent-selected features); raw-feature miners dR$ -2.3 / +0.9 / -11.1; random vocabulary +2.0 / -1.5 | Table 10 | verifier, admission, release shared across proposers |
| admission funnel (Sonnet) | 9,789 verifier checks, 10 verified, 2 cap-excluded, 8 admitted, 2 retired | | Table 16, cycles 3 to 9 | |
| active signatures after cycle 9 | Sonnet 11 (8 adm, 2 ret); Opus 20 (11 adm, 0 ret); GPT 25 (20 adm, 0 ret) | | Table 17 | GPT saturates the cap of 5 every growth cycle |
| Wilson z sensitivity | z=1.0: 11 rules, dF1 +8.0; z=1.64 and 1.96: 6 rules, +7.1; z=2.58: 6 rules, +6.8 | | Table 15 | not a formal multiple-testing control |
| history content (>=3 prior cohort, 5,650 tx) | correct history dF1 +17.8, block 4.50%; shuffled other-entity history dF1 -14.7, block 60.6%; no history -10.3 | CatBoost-periodical | Table 8 | |
| week-8 burst (n=206) | SR-Fraud dR +41.7, dR$ +46.4 | decision agent +38.4 / +34.8; CatBoost-periodical +9.2 / +6.6 | Table 4 | reflection could not learn this burst (outcomes mature after replay ends) |
| latency p50 / p95 | single-pass 1.31 s / 2.41 s; Reflexion 1.38 / 3.91; CoT agent 47.3 / 61.5 s | | Table 19, Sonnet 4.6 | |
| newer closed models | Opus 5 dF1 -7.3, Sonnet 5 -15.0, GPT-5.6 (sol) -12.5 as decision agents | Opus 4.5 -1.8, Sonnet 4.6 +1.8, GPT-5.4 -6.4 | Table 20 | "newer closed release fails to improve fraud detection" |
| self-hosted post-trained 9B (SR-Fraud-PT) | +5.4 / +10.5 / +7.8 / +20.1, p90 0.94 s | untrained 9B -18.8 / -9.1 / -15.2 / -25.0 | Table 5; Qwen3.5-9B, GRPO, LoRA r=32 | no symbolic state; about 4,000 training prompts |

## Mechanism details you could implement
- Separate the proposer from the admitter: the LLM only proposes a hypothesis space (atoms, qualifiers, bands) in strict JSON; code enumerates and verifies; rationale is stored but "never executed".
- Admission by lower confidence bound on matured outcomes with a margin over the current operating precision (gamma = 1.15, Wilson z = 1.0), minimum evidence counts (8 rows, 2 new true positives, 2 voting cycles), and a per-cycle cap (5).
- Retirement requires both weak recent evidence (Wilson upper bound below floor) and failure of the original gate, "to avoid pruning a pre-test-verified rule on a thin matured window".
- Maturation wall: policy for cycle j uses only outcomes through cycle j-2; each cycle scored once and frozen.
- Memory edits only the boundary band (r=3 escalate, r=4 release), never the base policy; the empty state reproduces the base agent exactly, which makes the memory's contribution directly measurable.
- Parse failures default to the safe action (allow), so a malformed output cannot move the operating rate.
- Optional human-review checkpoint on the knowledge-state changelog before deployment (Section 4 Ethics, Appendix E).

## Limitations, caveats, counter-evidence
- Authors' Limitations: Wilson bound "without a formal multiple-testing correction"; repeated full-stream replays "were not conducted because of their API and computational cost" (entity bootstrap covers sampling uncertainty only, not LLM stochasticity); one non-releasable production stream; off-policy replay (blocked transactions still appear in later histories).
- Case-control sample (all fraud, subsampled legitimate), so precision, F1 and block rates are cohort-conditional, not production figures.
- The Reflexion baseline uses "the least-guarded reflection prompt"; it isolates unverified reflection but is a weak form of it (inference: a partially self-verified free-text memory might drift less).
- Full SR-Fraud evaluated with Sonnet 4.6 only for the cross-backbone Reflexion diagnosis (Appendix D.4).
- Against the realistic baseline (monthly retrained CatBoost), only recall and dollar recall are significant.
- Domain gap: tabular fraud with ground-truth labels arriving by chargeback; engineering-agent outcomes (test pass, review acceptance) mature differently.
- Instruction-bearing content: none aimed at a reader's AI agent; the paper notes prompt-injection risk is reduced "but do not eliminate" by serializing content as data. No instructions followed.

## Takeaways for tuning a memory stack
- For lessons learned from failures (our H4 area), do not let an LLM write free text straight into next-run context; have it propose candidate rules, and admit a rule only when replay on matured outcomes clears a lower confidence bound and minimum counts, with a per-cycle cap.
- Measure the operating-point drift of any outcome-learned memory (here: block rate). Unverified reflection tripled to octupled the block rate at the same threshold. This is a direct measurement for B18.
- Design memory so the empty state reproduces the base agent; then "memory on vs off" is a clean arm.
- Keep a retirement rule with two conditions to avoid thrashing on thin recent data.
- Track admissions and retirements per cycle (Table 16, 17 style) as the memory's growth and churn metrics.

## Open questions
- How does a Reflexion variant with its own self-checks compare? Not tested.
- Variance over repeated LLM replays? Not run.
- Rate at which admitted rules later retire or turn harmful (a reinforcement-of-wrong-memory rate, B17)? Only counts are given: Sonnet retired 2 of 8 admitted; Opus and GPT retired 0.
- Would the gate work when outcomes are noisy proxies (test pass, reviewer approval) rather than chargebacks?

## Grading and labels
- Directness: medium. Write gate for outcome-learned rules measured end to end; not an engineering workload.
- Control: high. Maturation wall, matched arms, bootstrap CIs, static-state, proposer, history-shuffle and backbone controls.
- Independence: low. Single company, proprietary data, authors ran all arms; ground-truth labels rather than an LLM judge, so no judge-model sharing.
- Reproducibility: low. Data unreleasable; no code link found; prompts and thresholds published.
- Applicability: low-medium. The admission and retirement design transfers; numbers do not.
- Strength: paper-ablated.
- Pillars: R5 primary; R2 (admission and retirement of durable state), R4 (confidence-bounded automation), R8 (evidence cannot promote itself) secondary.
- Stage: write_gate.
- Tags: propose-verify, Wilson admission, retirement, maturation wall, verbal-reflection drift.
- Beliefs supports: B25 (LLM proposals never enter the policy without a deterministic verifier; the unverified arm destabilizes the operating point, Table 11); B18 (outcome-learning memory raised the guardrail-trigger rate, here block rate 14.80% to 41.44% vs 5% target, with no one intending it; this upgrades B18 from essay to one measurement).
- Beliefs contradicts: none.
- Beliefs would_create: verified admission with lower confidence bounds and a cap is required for outcome-learned memory; unverified reflection drifts the operating point.
- Contradiction: none found. B17 stands (no feedback-loop or wrong-reinforcement rate is reported; only admission and retirement counts). Consistent with synthesis section 1 ("treat every memory or skill write as a proposal").
- Priority: none matched (payment fraud; no System One model, ontology or benchmark terms).

## Origin chain
- Post: @RubberDucky_AI machine-generated roundup (2104583094078525629) -> arXiv 2609.27287 v1 -> Table 2 (overall), Table 7 (CIs), Table 11 (Reflexion drift), Tables 10, 16, 17, 18 (mechanism ablations).
- Independence: all data and authors from Coinbase / Ohio State; prior paper by the same authors (Tan, Ma, Zhang 2026, ACL) on LLMs for fraud data. Models: claude-opus-4-5, claude-sonnet-4-6, gpt-5.4 through an OpenAI-compatible gateway; reflection and decision may use the same model (diagonal R = D in main results; Table 14 varies them).

## Arm-vs-arm test implied (no card written)
- Arms: A = free-text lessons memory (after each failed engineering task, the agent appends a lesson that is injected next time); B = same lesson proposals, admitted only if replay on matured past tasks shows the lesson's trigger condition has Wilson lower-bound precision above the current rate with >= 8 matched cases, cap 5 per cycle, two-condition retirement; C = no lessons.
- Dataset: frozen harness, a time-ordered stream of our coding/review/incident tasks with outcomes (test pass, review acceptance), split into weekly cycles with a maturation lag.
- Metric: task pass rate and intervention/false-alarm rate (e.g., unnecessary refusals, extra reverts, or lesson-triggered regressions); lesson count and churn.
- Margin: B pass rate >= A and false-alarm rate <= C + 1 pp while A's exceeds it.
- Kill: B admits no lessons in 4 cycles (gate too strict for our volume) or A shows no drift.
- Decision it changes: whether our learning-from-outcomes path (H4) requires a verifier gate before any lesson enters context.
- Cost: M to L (needs a replayable outcome stream with maturation; our volume may be too low for Wilson counts, inference). Worth a card for the hypotheses agent tied to H4; not necessarily this quarter.
