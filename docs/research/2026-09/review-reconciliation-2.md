# Reconciliation of review 2 (pillars and the agent research loop), 2026-09-26

**Review:** [reviews/2026-09-26-review-2-pillars-and-loop.md](reviews/2026-09-26-review-2-pillars-and-loop.md). **Inputs it reviewed:** `review-prompt-pillars.md` and `t0-intelligence-handbook.md`. This file records what was adopted, what was held, and where each change landed.

## Adopted

| Finding | Change | Where |
|---|---|---|
| Separate topic labels from beliefs; version beliefs separately | Pillars are now a topic taxonomy with boundaries and labelling rules; a **belief register** (B1–B25) holds qualified statements, evidence for and against, grade, decision affected; beliefs change only by revision events on the bus | [programme-plan §1](programme-plan.md), [beliefs.md](beliefs.md), [brief §2](scraping-agent-brief.md), bus `beliefs/` |
| Add R8 Trust and governance; rename R4 Decision quality and abstention; keep R5 as a research area with a watch budget | Done; the reviewer's rewritten eight-row table is adopted as the taxonomy with boundaries added | programme plan, brief, handbook |
| Primary + secondary pillar, tags for mechanism / workload / lifecycle / evidence dimensions; `shared_state` and `cost` as cross-cutting tags | Card and note templates carry them; rubric step 6 | `queue/cards/TEMPLATE.md`, handbook §2 |
| Belief statements overstated: "no surveyed system", REALM attribution, "four in five", "will route around guardrails", 22-case bound | Each is restated with its denominator, survey bound or as a measurable risk in the register (B2, B3, B18, B20, B21) | beliefs.md |
| Evidence graded on five dimensions, not one ladder; verify the table not the abstract; claim-level dedup; origin chain; independence | Rubric steps 2–5; brief §3 | handbook, brief |
| Engagement prioritises, never sole discard; exploration sample; missed-item audit | Rubric step 1; delta metric | handbook §2, §7 |
| Trend object with maturity levels and coverage normalisation | Added to T0 outputs | programme plan T0 |
| Replace the card quota with informative experiments and decisions changed | Done everywhere the quota appeared | brief §8, handbook §7, programme plan |
| Missing execution contract: `runs/`, `reviews/`, verdicts require run bundle and review; roles (portfolio, challenger, executor, verdict, projector) with separated permissions | Folders created on Drive; templates; handbook §5; T5 roles in the programme plan | bus README v2, `queue/` templates |
| Drive ambiguities: 24-h windows, filename identity, newest-file state, index races, acceptance before spec, broken note refs, shared credentials, parking without retry, verdicts without artifacts | Checkpoints with consumed ids and durable backlog; envelope with `artifact_id`/`file_id`/`sha256`/`idempotency_key`; decision events name predecessor and expected prior state; single projector writes immutable index snapshots; spec uploaded and hashed before acceptance; `input_refs` everywhere; per-role uploader validation; `retry_after`/`attempts`/`blocked_reason`; verdict validity rule | bus README v2 rules 1–12, `checkpoints/`, templates |
| Untrusted inputs cannot authorise execution | Rule 10 on the bus; brief §9 | bus README, brief |
| Standing policy for autonomous runs; repository register authoritative, bus `experiments/` is its inbox | Stated; CTO to fill the policy in week 1 | programme plan §3b, bus README |
| Acceptance exercise before automation, including timeout, duplicate invocation and outage | Added to the week-1 checklist | handbook §8 |
| Reviewer joins as independent challenger, later bounded executor | Recorded as the T5 challenger role | programme plan T5, handbook §5 |

## Held

| Finding | Position |
|---|---|
| "Work R1, R6, R7 deeply this quarter" | Agreed on R1 and R6. R7 is worked through the proving grounds (open harnesses and the design partner) rather than as a standalone deep track, because its evidence comes from real swaps, not from a lab. R2 and R3 keep a minimal slice inside that work, as the reviewer says. |
| Multi-agent coordination as its own pillar | Held as a cross-cutting tag (`shared_state`) with R7 owning handoff contracts and R8 ownership and recovery, until volume warrants a pillar. This matches the reviewer's own conditional. |
| Cost as its own pillar | Held as a mandatory field on every experiment and a tag; R6 owns cost accounting. |

## Effect on earlier documents

- The seven-pillar tables in the programme plan and the brief are replaced; the review prompt for pillars stays as sent, with this reconciliation as its answer.
- The discovery plan's H-ids remain the experiment register; each hypothesis now names the beliefs it can revise (to be added on the next register edit).
- The first review's reconciliation is unchanged.
