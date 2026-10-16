# E-20260928-18-r2, PDLC trace-link part: can Jev type the links between tickets, pull requests, tests and designs?

We gave Jev 400 pairs of records from the public Apache OpenDAL project history (pull requests, CI runs, issues, design decisions, code modules). For each pair it answered five yes/no questions: does the first record implement, verify, refine, satisfy or block the second? We ran every pair three times (1,200 calls, 9 US cents) and scored the 300 test pairs against model-made gold labels. We compared Jev with the simple rules we would otherwise use: a ticket number in a pull request means "implements", a CI run on a pull request means "verifies", and so on. Jev's links are right more often. When Jev says a link exists, it has the right type 76% of the time, against 62% for the rules, a clear gain of 14 points. Jev is near perfect on "implements" (precision 0.98, recall 0.94). It is weak on "satisfies" (a module meeting a requirement), where it over-links. Overall quality across the four link types (macro-F1 0.71 against 0.68) is only slightly better, and not clearly so. Jev with the paper's fixed 0.60 cut did better than Jev with cuts fitted on the 100 development pairs (0.75 macro-F1, 93% of its links right): 100 pairs is too few to fit a cut for rare types. For Engram: Jev is a credible way to type trace links, especially "implements" and "verifies", and it filters out the rules' false links. Recommended next step: use the fixed 0.60 cut, keep rules as the candidate generator, and let Jev confirm the type. Before relying on it, compare against our LLM linker (needs OpenAI credits) and label the pairs Jev proposes outside this pool.

## Numbers (jev-1.13.0; 300 test pairs from 169 writes; 95% cluster-bootstrap intervals over writes, 10,000 resamples)

Gold (test): implements 56, verifies 51, refines 15, satisfies 11, blocks 0 (excluded), none 167.

| Arm | Macro-F1 (4 types) | Trace-link precision | Links predicted | implements P / R | verifies P / R | refines P / R | satisfies P / R |
|---|---|---|---|---|---|---|---|
| A-refit (thresholds fitted on 100 dev pairs, mean of 3 passes) | 0.706 | 0.760 | 136 | 0.98 / 0.94 | 0.93 / 0.61 | 0.79 / 0.76 | 0.24 / 0.73 |
| A-paper (0.60 for every type, mean of 3 passes) | **0.749** | **0.926** | 108 | 0.99 / 0.94 | 0.98 / 0.61 | 0.79 / 0.76 | 0.58 / 0.45 |
| C (deterministic rules) | 0.677 | 0.624 | 202 | 0.93 / 0.91 | 0.71 / 1.00 | 0.30 / 0.87 | 0.34 / 1.00 |

Paired differences:
- A-refit minus C, trace-link precision: +0.136 [+0.075, +0.198]. The spec's kill condition (interval wholly below zero) is not met.
- A-refit minus C, macro-F1: +0.029 [-0.049, +0.103]. Does not exclude zero.
- A-paper minus C, macro-F1: +0.072 [-0.033, +0.167].

Fitted thresholds (per pass): implements 0.45 to 0.50, verifies 0.50 to 0.55, refines 0.60, satisfies 0.35 to 0.40, blocks 0.30 (no dev support). Jev's predicted type agreed across all three passes on 94% of test pairs. Cost: 2.12M input tokens, 0.089 USD, 0.074 USD per 1,000 pair decisions, mean latency 0.38 s per pair.

Rule read-out: not negative. Not positive either: positive needs A-refit non-inferior to the LLM linker B within 2 points and at most one fifth of B's cost, and B was not run. A-refit beating C on macro-F1 with the interval above zero also fails. So **inconclusive**, with trace-link precision clearly in Jev's favour.

## Weaker than the spec wanted

- **No arm B** (the LLM linker on gpt-5.6-terra): the OpenAI key has no credits.
- **Candidate pool.** The 400 labelled pairs come from the deterministic and lexical generators only. Pairs Jev might propose outside that pool are neither scored nor labelled, so recall is conditional on this pool. No out-of-pool sample.
- **Unweighted.** The frozen sample records no inclusion probabilities, so metrics are unweighted rather than inverse-inclusion weighted.
- **Model labels.** Claude labels with Codex review (kappa 0.93), 18 contested rows, used as gold per policy v2.
- **Small dev slice.** 100 dev pairs (satisfies has only a handful), which is why the refit underperforms the fixed 0.60.
- **C comes from the frozen generator rules** (`generator_guess` in the candidate meta), the same rules the spec names, not a separately written implementation.
- **The rubric was put inside Jev's criteria**, lightly shortened for `satisfies` (the "use none for incidental touches" instruction became part of the true criterion). This follows the naming-audit finding: meaning goes in the definitions, not in the option names.
- **No answer endpoint here.** The LoCoMo answer comparison is in the sibling first-cut bundle; the 120 PDLC questions were not answered.
