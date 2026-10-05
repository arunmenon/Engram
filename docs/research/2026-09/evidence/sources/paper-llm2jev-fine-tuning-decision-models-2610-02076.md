---
schema_version: 1
artifact_id: N-SURVEY-20261004-04
artifact_type: note
producer: triage
run_id: survey-20261004T054506Z-478e
created_at: 2026-10-04T05:55:25Z
idempotency_key: note:survey:arxiv:2610.02076
input_refs: []
pillar_primary: R9
pillar_secondary: [R5]
memory_stage: none
priority: 2
related_notes: [N-20260929-07, N-SURVEY-20261004-01]
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: medium (how to fine-tune an open LLM into a decision model; general decision suites, not memory decisions)
  control: medium (training-free vs full fine-tune vs LoRA on the same base and evaluation; data selection informed by JevBench error analysis, flagged by the authors)
  independence: medium (Microsoft authors, no Jev affiliation; no product of their own)
  reproducibility: low (no code or data link found)
  applicability: high for priority 2 (the exact decision we face: tune an open model on a few thousand own decisions or not)
source_url: https://arxiv.org/abs/2610.02076
found_via: survey
---

# LLM2Jev: LLMs Are Already Jev-Style Decision Models, When and How to Fine-Tune Them (arXiv 2610.02076)

- **URL:** https://arxiv.org/abs/2610.02076 (HTML v1 read)
- **Type:** paper
- **Author / org:** Yinheng Li, Justin Wagle (Microsoft)
- **Date:** 2026-10-01
- **Retrieved:** 2026-10-04 (local copy: `out/log/raw/arxiv-2610.02076.html`)
- **Cited by evidence:** survey question R9-1 (can we run and tune a decision model ourselves, and with how much data?)
- **Relevance to a memory stack:** high. It is a controlled warning that naive fine-tuning on narrow decisions degrades general decision quality, and it gives a LoRA recipe that does not.

## TL;DR

- With no training, a frozen Qwen3.5-4B read as a listwise decision model "correctly resolves 188 of the 231 public JevBench instances (81.4%)". Greedy generation picks the same option on all 231.
- Full fine-tuning on intent data improved Banking77 but hurt general decisions: "JevBench accuracy drops from 81.4% (zero-shot) to 79.2% at 100 steps and 76.2% after a full epoch, even as in-distribution validation loss continues to improve monotonically."
- The failure modes after one epoch: "an aggressive confirmation bias toward 'yes' on binary verification queries, severe suppression of 'none of the above' fallback options, reliance on superficial lexical matches". A write gate or link gate would suffer exactly these (inference).
- "Only parameter-efficient adaptation via LoRA manages to improve the 4B baseline on JevBench (+2.6 points)", reaching 84.0%.
- "On public JevBench, jev-local achieves only 74.9% accuracy with a frozen Qwen3.5-9B", which trails the 4B listwise readout.

## What it claims / describes

- **Readout.** Each option gets a bracketed numeric ID. Next-token log-probabilities over the ID tokens are combined into a softmax over options, so no text is generated.
- **Fine-tuning loss.** A tree-factorised listwise cross-entropy plus three KL anchors: legal token mass, illegal token distribution, and non-decision positions. The anchors keep normal generation intact (λ = 1, per the reader extract).
- **Models.** Qwen3.5-4B and Qwen3-0.6B, each run training-free, fully fine-tuned, and with LoRA (rank 16, alpha 32, on decoder linear layers). Comparators named: SemIf, reflex 4B, open-alternative-jev, jev-local, Winnow-12B and GPT-5.6 Sol.
- **Data.** Intent sets: Intent-100 is 3,000 examples, Intent-1ep is 95,461, drawn from CLINC150, MASSIVE and Bitext. Reasoning mixtures: ProofWriter, RulesQA, LogiQA2, PIQA, CosmosQA, SocialIQA. Long-context mixture: ContractNLI, MuSiQue, QuALITY.
- **Recipe.** 1 epoch, global batch 32, lr 2e-6 (4B full), 5e-6 (0.6B), 1e-4 (LoRA); 4x A100 80GB (from the reader extract).

## Numbers

| System | JevBench public acc | Hard | ECE | External macro | Banking77 | Source check |
|---|---|---|---|---|---|---|
| Qwen3.5-4B training-free | 81.4 | 64.9 | .057 | 78.6 | 69.0 | 81.4 verified in text |
| Qwen3.5-4B full fine-tune | 80.5 | 61.3 | .079 | 78.3 | 75.9 | text: "76.2 to 80.5% vs. 81.4%" |
| Qwen3.5-4B LoRA | 84.0 | 67.6 | .067 | 79.2 | 74.2 | 84.0 verified |
| SemIf (frozen 4B) | 80.5 | 60.4 | .061 | 75.4 | not stated | reader extract |
| reflex 4B | 79.7 | 59.5 | .070 | 78.8 | not stated | reader extract |
| Qwen3-0.6B training-free | 56.7 | 33.3 | .278 | 57.9 | 22.2 | reader extract |
| Qwen3-0.6B full fine-tune | 57.1 | 34.2 | .133 | 58.2 | 59.8 | reader extract |
| jev-local (frozen Qwen3.5-9B) | 74.9 | | | | | verified in text |

| Other | Value | Caveat |
|---|---|---|
| Full fine-tune trajectory | 81.4 (0 steps), 79.2 (100 steps), 76.2 (1 epoch) | in-distribution loss kept improving |
| Latency | "median latency is 194 ms for 4B and 76 ms for 0.6B; SemIf takes 46 ms in BF16" | single RTX A5500, FP32, "not optimized for speed" |
| Hosted Jev on the same items | not reported in the parts read | JevBench's own published Jev figure is 86.6% on public items (see N-SURVEY-20261004-01) |

Judge shared with system: not applicable (gold labels). Cost: not stated.

## Mechanism details you could implement

- Read any instruct LLM as a decision model by scoring option-ID tokens. Check parity with greedy generation as a sanity test; the authors found the two identical on all 231 items.
- Fine-tune with LoRA (rank 16, alpha 32) rather than full parameters. Add KL anchors so the model keeps its prior over options outside the training distribution.
- Watch for the three drift signatures on a held-out general suite during training, not just in-domain loss: yes-bias, suppression of "none of the above", and lexical shortcuts.

## Limitations, caveats, counter-evidence

- The authors write: "Because subsequent data iterations were motivated by error analysis on public JevBench samples, we treat the evaluations ... as exploratory". The LoRA gain is therefore optimistic.
- No code or data link was found, and there is one base model family.
- The public JevBench items are close to saturated as a separator (see N-SURVEY-20261004-01). The +2.6 LoRA gain is about 6 items out of 231.
- Hosted Jev was not run head to head in the sections read.

## Takeaways for tuning a memory stack

- If we fine-tune an open model on our own memory decisions, use LoRA with anchors. Keep a general held-out decision suite in the evaluation, because own-task loss will look better while general judgement gets worse.
- A frozen 4B listwise readout (81.4%) is a credible zero-training baseline arm for any self-hosting test. It costs nothing to set up.
- The yes-bias failure mode matters most for a write gate. A model that learns to say "store" more often will silently grow the store (inference).

## Open questions

- Does the degradation appear when the fine-tuning data is a mix of our own write-gate, link-type and staleness decisions rather than one intent task?
- How many own decisions does LoRA need before it beats the frozen readout on our held-out memory decisions?
