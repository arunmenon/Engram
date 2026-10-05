---
schema_version: 1
artifact_id: N-SURVEY-20261002-05
artifact_type: note
producer: triage
run_id: survey-20261002T054505Z-3d1e
created_at: 2026-10-02T06:30:00Z
idempotency_key: note:survey:arxiv:2610.00450
input_refs: []
pillar_primary: R8
pillar_secondary: [R2]
memory_stage: safety
beliefs_affected:
  supports: [B25]
  contradicts: []
evidence:
  directness: high (persistent workspace memory poisoning across sessions in an OpenClaw-style agent, measured by artifact-level verifiers)
  control: high (5 baselines plus No Defense, 3 ablations, benign-only vs malicious-only promotion control, 2 defense-aware attacks)
  independence: low (authors built attacks, scenarios, verifiers and the defense; Workspace-Bench utility judge is Claude Sonnet 4.6, also the main backbone, though the task model there is GPT-5.5)
  reproducibility: medium (code released at github.com/euph00/ZoneClaw-code; 15 trials per setting; provider models may drift)
  applicability: medium (CUA email/chat/forum/marketplace tasks, not coding; but the flat AGENTS.md / MEMORY.md / TOOLS.md workspace maps directly onto coding-agent memory files)
source_url: https://arxiv.org/abs/2610.00450
found_via: survey
---
# ZoneClaw: Mitigating Persistent Memory Attacks by Establishing Memory-Zoning in OpenClaw-Style Computer-Use Agents

- **URL:** https://arxiv.org/abs/2610.00450 (HTML https://arxiv.org/html/2610.00450)
- **Type:** paper
- **Author / org:** Haokai Ma, Chieh Lin, Yupeng Qiu, Ee-Chien Chang (National University of Singapore)
- **Date:** not stated on page (arXiv id implies Oct 2026)
- **Retrieved:** 2026-10-02 (local copy: /Users/arunmenon/MemoryRSI-Signals/work/survey/survey-20261002T054505Z-3d1e/out/log/src/2610.00450.html)
- **Cited by evidence:** survey R8
- **Relevance to a memory stack:** high, it is a controlled test that structural authority (where a memory came from and whether it was corroborated) beats per-write or per-action content judgment on persistent memory poisoning.

## TL;DR
- Flat workspace memory gives remembered external claims the same authority as user instructions; ZoneClaw splits memory into Policy (D0), Trusted (D1) and Untrusted (D2) zones and only a Gatekeeper may promote D2 to D1, after cross-checking against D0/D1.
- Headline: "ZoneClaw drives ASR from 372/480 to 6/480 while retaining utility in 458/480 trials" across 4 scenarios, 2 injection settings, 4 backbones.
- Attacker claims still persist in D2 (60/60 and 59/60 trials on Sonnet 4.6) but CSR (crossing into authority) is 0/60; defense is "withholding authority rather than rejecting external information".
- Content-judging baselines (write-time Watcher, action-time ClawGuard) each leave at least one scenario largely undefended; provenance corruption claims "read as ordinary factual updates and offer the audit nothing to reject".
- Removing the cross-check lets attacker claims cross the authority boundary in 21/30 and 25/30 trials, so an LLM gatekeeper without trusted reference context is not enough.

## What it claims / describes
Threat: attacker controls only benign-looking external content; the agent records an attacker-favored claim during a legitimate task; a later, unrelated session reloads it and acts on it. Two attack classes: hidden side effects (BCC Exfiltration, Chat Mirror) and provenance corruption (Source Redirection, Marketplace). Two injection settings (user-triggered, scheduled). Four processes: Planner (reads D0, D1), Observer (reads external content, writes D2 with source, no outward actions), Gatekeeper (only promoter D2 to D1, cross-checks against D0/D1), Executor (acts using D0, D1, never reads D2). Enforcement is "role-scoped contexts and tool policies rather than kernel-enforced access controls".

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| ASR, all backbones | 6/480 | 372/480 No Defense | 4 scenarios x 2 settings x 4 backbones x 15 trials | the 6 are Qwen3.7-Plus Source Redirection, "each at 3/15" |
| Utility, all backbones | 458/480 | not stated in aggregate | same | per backbone 114/120 Sonnet 4.6, 119/120 GPT-5.5, 114/120 GLM-5.2, 111/120 Qwen3.7-Plus |
| ASR Sonnet 4.6 | 0/15 in all 8 combinations | No Defense BCC 12/15 and 9/15; ISR/ASR text values 0.87/1.00 Chat Mirror, 1.00/1.00 Source Redirection, 0.67/0.53 Marketplace | Table 2 | n=15 per cell |
| Watcher (write-time content audit) ASR | BCC 6/15 and 2/15; Chat Mirror 14/15 and 12/15 | No Defense BCC 12/15, 9/15 | Sonnet 4.6 | write-time screening fails on plausible-looking destinations |
| ClawGuard (action guard) | BCC ASR 0/15 both settings, Utility 9/15 and 11/15; Chat Mirror 13/15 and 15/15 | | Sonnet 4.6 | blocks anomalous outside recipients only |
| PrivSep | BCC 1/15 and 0/15; scheduled Source Redirection 13/15 | | Sonnet 4.6 | lowest baseline ASR overall |
| Provenance-corruption Utility | no baseline exceeds 16/60 | 12/60 No Defense | Sonnet 4.6 | ZoneClaw 59/60 |
| Selective promotion | benign facts cross B2 in 30/30 trials (90 promotions); malicious claim retained in D2 29/30, crosses B2 0/30 | | user-triggered BCC, Sonnet 4.6, 30 trials each | one malicious-only miss was Observer transcription incompleteness |
| Ablation w/o Cross-check | CSR 21/30 and 25/30 | ZoneClaw 0/30 | Table 4, Sonnet 4.6 | low ASR there is B3 absorbing a B2 failure |
| Ablation w/o Gatekeeper | 30/30 claims cross B2, ASR 15/30, Utility 20/30 hidden side effects | | Table 4 | zoning without a gate is worse than no zoning on utility |
| Defense-aware attacks | Corroboration Planting CSR 0/15, ASR 0/15, Utility 15/15; Claim Fragmentation same | No Defense ASR 11/15 and 15/15 | Table 5, BCC user-triggered, Sonnet 4.6 | only 2 adaptive strategies, one scenario |
| Repeated injection (10 sessions) | ZoneClaw CSR and ASR 0/3 at every update | No Defense ASR 3/3 from update 1 | Table 11 | n=3 runs |
| Benign utility, Workspace-Bench-Lite 30 tasks | 47.0% mean score, TCR@80 8/30 | 50.6%, 10/30 No Defense; PrivSep 39.2%, 7/30 | GPT-5.5 task model, Sonnet 4.6 judge | paired bootstrap 95% CI [-10.7, 2.2] pp, not significant |
| Overhead | 1.07x tokens, 1.74x API cost, 2.26x latency vs No Defense | other defenses 390.6k to 501.4k input tokens vs 173.2k | Table 10, BCC user-triggered, 15 trials | caption says Qwen3.7-Plus at medium reasoning, cost estimated from list prices; latency is worst among defenses |

Text vs table: abstract says "four backbones"; Section 4.6 text says GPT-5.5 "0/15 on all combinations" and C.9 confirms 30 of 32 backbone-setting combinations at 0/15. Consistent. Overhead paragraph does not name its backbone; Table 10 caption says Qwen3.7-Plus at medium reasoning (flag: not cross-checked against table cells).

## Mechanism details you could implement
- Three zones as separate files: immutable policy, trusted operational memory (user-admitted or cross-checked facts), untrusted observations stored with source.
- Hard role split: the process that reads untrusted content cannot act outward; the process that acts never reads the untrusted zone.
- Promotion requires corroboration against content the attacker cannot write (D0/D1), judged on "what each claim asks for", not on how often it was seen.
- Each fragment must qualify alone; planted corroboration must itself be promoted before it counts.
- Measure three boundaries separately: ISR (persisted), CSR (gained authority), ASR (caused action).

## Limitations, caveats, counter-evidence
- Not OS-enforced; a prompt-scoped role violation is not tested beyond the 2 adaptive attacks.
- 15 trials per cell; authors wrote attacks, verifiers and defense.
- Gatekeeper is an LLM; correctness depends on D1 already holding the right reference (e.g., approved channel). Novel legitimate facts with no D1 anchor: behavior on those beyond the 3 benign facts test is not stated.
- Latency 2.26x; planner-to-executor handoff caused utility failures (Appendix D.2).
- CUA domain, not coding agents.

## Takeaways for tuning a memory stack
- Supports B25: extracted memory must not authorise its own promotion; promotion needs an independent anchor the writer cannot touch.
- Relative to B24: content screening at write time (Watcher) is the weakest arm here; a provenance/authority gate dominates it. A 20/22 content gate result should be read as likely scenario-dependent (inference).
- Track CSR (authority crossings), not just ASR.

## Open questions
- How does the gate handle legitimate new conventions (new build commands, new repo rules) with no trusted anchor? (not stated)
- Performance with a cheaper Gatekeeper model? (not stated, suggested as future work)
- Coding-agent scenarios (CLAUDE.md, AGENTS.md edits proposed from tool output)? (not tested)
