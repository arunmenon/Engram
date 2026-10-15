# Research grounding and working definition

Researched 15 October 2026. This skill is a qualitative artifact-review method, not a validated slop detector, formal standard or automated CI enforcement system. Its seven dimensions are our synthesis of the sources and practical deliverable failures.

## Why unpack the term

Merriam-Webster associates slop with low-quality digital output produced at volume using AI. That identifies a cultural phenomenon but does not supply an artifact-level test of quality. Its [publisher-issued announcement](https://www.globenewswire.com/news-release/2025/12/15/3205236/0/en/merriam-webster-announces-slop-as-the-2025-word-of-the-year.html) is a primary lexical source, not an empirical evaluation method.

Daniel Singer's September 2026 [commentary in npj Artificial Intelligence](https://www.nature.com/articles/s44387-026-00161-8) argues that the label can hide differing broader judgments about AI. This is philosophical commentary, not evidence that a particular checklist detects defects. For our workflow, replace the label with observable failures of evidence, reasoning, usefulness or justified complexity.

Working definition: avoidable content or implementation that appears useful or complete but fails to provide justified value for its stated purpose. A concise artifact can fail; a long, rigorous artifact can pass. This definition deliberately evaluates the artifact regardless of authorship.

## Sources supporting the checks

- [NIST AI 600-1, Generative AI Profile (2024)](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf), sections 2.2/2.7 and actions MS-2.5-001/003: describes confidently erroneous content, information integrity and source verification; cautions against extrapolating from narrow assessments. Supports grounding and scope-of-proof checks. It does not define this skill's gate or certify its effectiveness.
- [Google Engineering Practices: what to look for in code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html): evaluates design/functionality, excessive generalization, understandable code and meaningful tests; distinguishes optional personal style from blocking defects. Supports necessity and maintainability checks. These are engineering guidelines, not a study of AI-generated code.
- [Lee et al., CHI 2025: GenAI and critical thinking](https://www.microsoft.com/en-us/research/publication/the-impact-of-generative-ai-on-critical-thinking-self-reported-reductions-in-cognitive-effort-and-confidence-effects-from-a-survey-of-knowledge-workers/): surveys 319 knowledge workers and describes associations between confidence and reported critical-thinking effort. Supports deliberate verification/integration rather than accepting polish. The self-reported study does not establish that AI always reduces reasoning or that this gate prevents it.
- [Liang et al., GPT detectors are biased against non-native English writers (2023)](https://arxiv.org/abs/2304.02819): reports false classifications and detector evasion in its tested settings. Supports rejecting style/authorship detection as the objective. It does not prove every detector has identical performance.
- [Liu et al., Beyond Functional Correctness (updated 2026)](https://arxiv.org/abs/2404.00971): investigates code hallucinations across evaluated models/benchmarks. Supports inspecting code-specific unsupported behavior rather than treating compilation as sufficient. Its taxonomy is not copied wholesale into this skill and does not establish present-model failure rates.

## What the gate can and cannot establish

A review can identify a contradictory claim, unjustified abstraction, missing prerequisite or misleading diagram in a specified revision. It cannot determine intent, reliably infer AI authorship, guarantee reader comprehension or replace required execution, specialist review or stakeholder judgment. PASS means the declared review found no unresolved material issue; it does not mean “zero slop” universally.

No banned-word list, word-count target, numeric slop percentage or appearance-based AI classifier is used. Factual/behavioral uncertainty and optional style improvements remain separate from demonstrated defects.
