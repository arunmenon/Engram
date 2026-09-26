# China AI Bulletin 12 (RSI parts only)

- **URL:** https://chinaaibulletin.substack.com/p/china-ai-bulletin-12
- **Type:** essay (newsletter)
- **Author / org:** Emmie Hine
- **Date:** 2026-09-25
- **Retrieved:** 2026-09-26 (no local copy)
- **Cited by evidence:** RSI as an explicit oversight object / 2026-09-25 EmmieHine
- **Relevance to a memory stack:** medium. The cited taxonomy defines RSI levels by what persists and who chooses the improvement, which maps directly onto how autonomous a memory stack is.

## TL;DR
- Cites "The Last AI Built by Humans: Toward Genuine Recursive Self-Improvement" (https://arxiv.org/abs/2609.11873), led by Shanghai Jiao Tong University and Theseus Labs with Tsinghua, Shanghai AI Lab, ByteDance, ModelBest, Xiaohongshu's Super Intelligence Team and others.
- Ladder B0 to L5. "Full L5 has not yet been demonstrated", two systems show bounded L5 traits; in software engineering "L2 is the strongest established level".
- Other RSI items: Alibaba says Qwen3.8-Max improved its Artificial Analysis score "from 40 to 45" over 33 cycles; an Atria Dawn technical report studies how "56 researchers used AI agents to build the model".

## What it claims / describes
- **B0**: in-task improvement, "no persistent change".
- **L1**: AI executes human-defined improvements; results persist across tasks.
- **L2**: AI selects improvement methods while "objective and evaluation criteria stay fixed".
- **L3**: AI determines what experience it needs (task generation, self-play).
- **L4**: AI revises persistent state using deployment environment interaction.
- **L5**: meta-improvement; AI "revises the mechanisms that govern its later improvement".
The two bounded-L5 systems are not named in the bulletin excerpt I retrieved.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Qwen3.8-Max Artificial Analysis score | 45 | 40 | 33 improvement cycles | Alibaba self-report; ~0.15 pts/cycle average (inference) |
| Atria Dawn | 56 researchers using AI agents | | | no outcome number given |

## Mechanism details you could implement
- Use the ladder as a classification of your own stack: a memory that stores notes across sessions is L1/L2; one that picks its own write rules against a fixed eval is L2; one that learns from live deployment is L4; one that rewrites its consolidation/eval policy is L5 (inference).

## Limitations, caveats, counter-evidence
- Secondhand summary of the paper; level definitions paraphrased by the newsletter.

## Takeaways for tuning a memory stack
- EvoSkill and RRSI are L2 (fixed objective and evaluator, AI picks edits). Mallen's risk sits at L4 (learning from deployment). Decide deliberately which level you allow, and keep the evaluator fixed and outside the memory's write path if you want to stay at L2.

## Open questions
- Which two systems show bounded L5?

---
