# RRSI: Regularized Recursive Self-Improvement of Agent Harnesses

- **URL:** https://regularized-rsi.com/ ; paper https://arxiv.org/abs/2609.24972 ; code github.com/google-research/rrsi
- **Type:** paper (+ project page)
- **Author / org:** Peng Xia, Rujun Han, Zifeng Wang, Yanfei Chen, Yufan Zhuang, Yoonho Lee, Chengsong Huang, Han Yu, Zhongying CuiZhu, Yifei Ming, Huaxiu Yao, Burak Gokturk, Tomas Pfister, Chen-Yu Lee (Google Cloud AI Research, UNC-Chapel Hill, Stanford, WashU St. Louis)
- **Date:** arXiv v1 2026-09-21, v2 2026-09-23
- **Retrieved:** 2026-09-26 (no local copy; WebFetch of project page, arxiv abs and arxiv HTML)
- **Cited by evidence:** Frozen-model self-improvement through harness and skills / 2026-09-25 vigram_void
- **Relevance to a memory stack:** high. Memory, skill and context_mgmt are editable harness components, and the four regularizers are directly usable as write/consolidate/forget gates for a self-tuning memory stack.

## TL;DR
- Problem: self-improving harnesses "learn the benchmark they are scored on"; prior methods' evolve-set gains "shrink or vanish once the benchmark changes", and two prior methods ended below the harness they started from.
- Fix: regularize the search, not the harness. Four controls: annealed edit budget, leakage critic, noise-adjusted acceptance floor with a token cost rule, and a pruner for components that stopped helping. Plus a ledger of every hypothesis, diff and result.
- Frozen Claude Opus 4.8 policy: Terminal-Bench 2.1 74.2 to 80.2, SWE-bench Verified 82.0 to 83.8, Frontier-Eng +4.3 Medal points (post says 17.7 to 22.0; the paper extraction gave the +4.3 delta only).
- Transfer: +3.4 pts average on six held-out benchmarks (all improve), +4.0 on the evolve set; final harness uses 2.42M vs 3.80M policy tokens per trial (-36%).
- Ablation: dropping regularizers raises evolve-set score and lowers out-of-distribution score. Classic overfitting signature.

## What it claims / describes
Harness = "prompts, control flow, tooling, memory, and context management surrounding the frozen backbone model". Nine editable component labels: `prompt, control_flow, config, output_plumbing, context_mgmt, client_tool, skill, memory, subagent`. "every harness component stays editable".

One round:
1. **Proposal**: proposer reads the full ledger of prior candidates and outcomes and produces a candidate under a shrinking edit budget.
2. **Critic**: screens for leakage before scoring.
3. **Gate**: candidate admitted only if its gain clears a noise floor measured on the unchanged base harness H0, and its extra tokens are paid for by gain.
4. **Pruner**: components with no recent measured gain are reported to the proposer as deletion targets.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Terminal-Bench 2.1 | 80.2 | 74.2 (H0) | Opus 4.8 frozen | |
| SWE-bench Verified | 83.8 | 82.0 | same | |
| Frontier-Eng | +4.3 Medal points (post: 17.7 to 22.0) | H0 | same | post figure not independently confirmed |
| Evolve-set avg gain | +4.0 pts | H0 | 3 evolve benchmarks | project page |
| Held-out avg gain | +3.4 pts, all six improve | H0 | 6 held-out benchmarks | abstract says "up to 4.7 points on the five out-of-distribution benchmarks" and "up to 14.1 points on the split it evolves against"; counts differ between page and abstract |
| Max held-out advantage over prior avg | up to 22.9% | avg prior method | | |
| Policy tokens / trial | 2.42M | 3.80M unregularized, 3.80M AHE, 3.59M w/o acceptance regularizers | | -36% (page); abstract says 30% fewer |
| Harvey LAB evolve / ID held-out / OOD avg | RRSI 90.5 / 89.2 / 43.6 | H0 89.4 / 86.9 / 39.7; Meta-Harness 93.0 / 89.2 / 40.6; AHE 90.7 / 88.7 / 41.9; TTHE 91.1 / 88.5 / 41.0; HarnessX 91.8 / 89.1 / 41.4 | agentic workspace | RRSI has the lowest evolve score of evolved methods but best OOD |
| Ablation: no acceptance regularizers | evolve 91.5, OOD 41.0, tokens +48% | RRSI | Harvey LAB | |
| Ablation: no proposal regularizers | OOD -1.7, evolve roughly unchanged | RRSI | | |
| Ablation: no regularizers | evolve 92.8, OOD 40.3 | RRSI | | |

Benchmarks: coding (Terminal-Bench, SWE-bench Verified), agentic workspace (Harvey LAB, JobBench, APEX-Agents), engineering design (GDPval, EngDesign, Frontier-Eng).

## Mechanism details you could implement
- **Annealed edit budget** (cosine): `b_t = ceil(b_min + (b_max - b_min) * 0.5 * (1 + cos(pi * t / T)))`. "Early rounds may bundle a few coordinated edits to find a mechanism; late rounds get one attributable change." b_min, b_max, T values: not stated in what I retrieved.
- **Leakage critic**: "rejects edits that explicitly encode task names, entity names, task-specific values, answers, or other logic specific to the evolve benchmark", applied before scoring.
- **Noise floor**: "Before evolution, the unchanged base harness is evaluated repeatedly to estimate the empirical noise tolerance delta." Accept only if dS > delta. Number of repeats and multiplier: not stated.
- **Cost rule**: for dS > delta, require `dC <= beta0 + beta1 * dS` where dC is relative policy-token cost change. beta values: not stated.
- **Pruner**: within window n_prune, if a component's "best recent measured gain" <= 0, it is reported to the proposer as a deletion target. Pruner removes changes "too small, too expensive, or no longer useful".
- **Ledger schema**: `(t_i, l_i, h_i, d_i, dS_i, dC_i, a_i)` = round, component, hypothesis, diff, score delta, cost delta, accepted flag. Purpose (per vigram_void): "so failed ideas stay failed".
- Which components the final harness actually changed (memory vs others): not stated.

## Limitations, caveats, counter-evidence
- Paper: harness-level only, frozen backbone; "still relies on a finite evolve set and several regularization hyperparameters"; broader validation across agent architectures needed.
- Inconsistent summary numbers between project page (6 held-out, -36%) and abstract (5 OOD, 30%). Possibly v1 vs v2 (inference).
- Evolve-set scores are lower than unregularized methods; you trade in-distribution gain for transfer.
- Nothing isolates the memory component's contribution.

## Takeaways for tuning a memory stack
- Before tuning, run the unchanged memory config N times and use the spread as the minimum gain a change must beat. Most small memory-tuning "wins" are probably noise (inference).
- Charge memory for tokens: a new retrieval layer or longer injected context must buy gain at a stated rate (dC <= b0 + b1*dS).
- Anneal: allow bundled memory redesigns early, then one attributable change per round.
- Run a leakage critic over written memories: reject entries that name specific eval tasks, entities or answers. This is the memory analogue of "the harness starts learning the test".
- Prune memory components (and arguably entries) whose recent measured contribution is <= 0.
- Keep the change ledger outside the memory it tunes, and always report held-out, not just tuning-set, scores.

## Open questions
- Values of b_min, b_max, T, n_prune, beta0, beta1, and number of H0 repeats.
- Did evolved harnesses edit the memory component, and did those edits transfer?
- Does the regularized loop keep compounding past the reported rounds, or plateau?

---
