# Research loop: state, reconciliation and the two open questions

**Date:** 2026-09-27. **Inputs:** the [builder's briefing](research-loop-briefing-2026-09-27.md) of the loop as built on the Mac, against this pack's [handbook](t0-intelligence-handbook.md), [brief](scraping-agent-brief.md) and [bus contract](../queue/README.md). **Rule from here:** the bus README v4 at the Drive root and `bin/bus.py` are authoritative for the wire contract; the repository documents describe intent and are corrected to match reality below, not the other way round.

## 1. What was built beyond the plan, and is kept

| Built | Plan said | Verdict |
|---|---|---|
| Status chain `proposed → recommended \| merged \| rejected` (hypotheses) `→ accepted \| rejected \| deferred` (person); `overruled` returns to `recommended`; publisher refuses `accepted` from an agent | hypotheses agent writes `accepted`; a person merges fortnightly | **Better.** The person owns the gate daily, not fortnightly. Adopt in the handbook. |
| Execution packet inside each spec (harness command, dataset, baseline, metric script, budget, kill rule, output manifest) | spec fields only | **Better.** It is what makes an executor a runner rather than a planner. |
| `briefs/` and a desk with a five-line card per recommendation | weekly delta only | **Better.** Adopt. Density is question 2 below. |
| Challenger as Codex on a schedule, reviewing every spec and a 20 % decision sample | challenger on trigger | **Better.** Different model family, as review 2 asked. |
| Jev shadow inside triage: pillar, five evidence scores, same-claim per note; hidden from the agent; agreement logged | not in the handbook | **Good, and exactly the discipline the catalogue prescribes.** One week of shadow before any pruning or dedup authority. Add the agreement numbers to the weekly delta. |
| Desk projector every 30 min; deterministic fold by predecessor; duplicates folded by hash; telemetry-based health | Monday projector only | **Better.** |
| Bounded auto-apply of handle changes | owner applies all config | **Acceptable** with the stated bounds. Query changes still wait for the owner. |
| Serialised uploads under a machine-wide lock after a six-duplicate race | idempotency key check | **Necessary.** Keep both. |
| Mirror to branch `research-bus-mirror`, committed locally, no push | delta job pushes a branch | Fine for now. Pushing is a CTO action until a deploy key exists. |

## 2. What is still missing, in priority order

1. **Executor, verdict role, belief revisions.** Approved specs queue with nowhere to run. This is the P3 frozen harness in the discovery plan plus a runner. It lives in this repository, not on the Mac.
2. **Standing policy** (`policy.md`): without it the executor must refuse everything. Draft below for the CTO to set.
3. **Top-down intake** (question 1 below).
4. **Hygiene from the briefing:** rotate the Jev key; `pmset -c sleep 0`; rclone client id migration; replace placeholder owner codes T2–T5.

## 3. Corrections to the repository documents

- Handbook §4–§5: status vocabulary and roles replaced by the built chain; the hypotheses role recommends, never accepts; briefs and desk added; the projector runs every 30 min and the Monday delta writes the memo and mirror. Jev shadow added as §2b.
- Bus README in `queue/`: marked as the mirror of Drive README v4; folder table gains `briefs/`, `desk/`, `telemetry/`; the two rewritten pointers are named.
- Brief §6: unchanged in substance; wording aligned.

## 4. Question 1: bottom-up only?

**No. Add the top-down pass, and add a third intake the briefing does not mention.**

*Top-down survey pass (agree with the proposal, with three constraints).* One job, `survey`, weekly per pillar, two pillars a day, starting with R1, R5, R7, R8. Input per pillar: the thesis, the open beliefs in `beliefs.md` with grade `lead` or `open`, and open watch requests. It searches arXiv (listing API by category and date, then abstract and table read), GitHub (releases and READMEs at pinned commits for the landscape set plus new hits), and vendor docs. It writes through the same templates and folders, with `producer: survey` and a `discovery: top-down` tag, and dedupes by the same-claim check against existing notes. Constraints: (a) a survey note must cite a primary source it actually opened, never a search snippet; (b) survey cards carry the same card budget as triage and enter the same hypotheses queue, so they compete on decision value rather than bypassing the gate; (c) the weekly delta reports bottom-up and top-down yields separately, so we learn which intake produces cards that survive.

*Third intake: our own failures.* Review 2 asked for a demand and problem register beside the literature register. Feed it from three places the loop already touches: verdicts that come back `inconclusive` or `kill` (each is a watch request for counter-evidence), triage's parked-for-no-source backlog (a signal about what the field asserts without evidence), and, once the executor exists, run failures. This is cheap and it is the only intake that measures us rather than the field.

## 5. Question 2: brief density

Keep version 2.2 and measure it instead of iterating on taste. Two numbers per week from the desk: median seconds from card open to decision, and the share of decisions where the CTO opened the full brief before deciding. If the second number is below one in five, the five-line card is carrying the decision and the full brief can shrink to its evidence and risk sections. If the CTO overrules the challenger more than one time in five, the "what the reviewer worries about" line is not doing its job and moves to the top of the card. The brief's fixed skeleton stays: fit, question, why now, evidence in a word, reviewer's worry and whether it blocks, what approving commits to, suggested action.

## 6. Draft standing policy for autonomous runs (for the CTO to set; not in force)

```yaml
policy_version: 0.1-draft
authorised_executor: executor role on the Engram harness host only
preconditions: person `accepted` decision + spec with execution packet + challenger review `ready` where review_required
datasets_permitted: [public benchmarks listed in discovery-plan P3, seeded fixtures from T1, dogfood corpus tenants named by the CTO]
datasets_forbidden: [anything from the design partner unless explicitly listed, anything containing secrets or personal data]
budget_per_run: {tokens: 2_000_000, cost_usd: 25, wall_clock_h: 2}
budget_per_week: {cost_usd: 150, runs: 12}
concurrency: 1
environment: pinned harness commit, frozen `evaluate()`, no network except model endpoints and the bus
review_required_when: [cost_usd > 10, beliefs_affected includes a `firm` or `working` belief, novelty claim, contradicts an open note, promotion to production shadow]
on_failure: write a `runs/` bundle with status failed; never retry silently; never rerun without a new spec revision
never: executor writes verdicts; executor modifies specs, datasets or scorer; any run without a person's `accepted`
```

## 7. Executor: what it is and where it lives

A runner in this repository (`tests/eval/` alongside the frozen harness), invoked by a scheduled job on the harness host, not on the scraper Mac. It polls `decisions/` for `accepted` with no `runs/` bundle, validates the policy preconditions, downloads the spec and checks its hash, executes the packet's harness command inside the pinned environment, and uploads a complete `runs/` bundle with manifest, raw outputs, resources and deviations. A separate verdict job reads the bundle and the review, applies the spec's predeclared margin and outcome actions, writes `verdicts/`, and emits `beliefs/` revision events. Both roles refuse to certify their own output. The first acceptance run is the exercise from review 2: one accepted spec, an interrupted upload, a duplicate invocation, and an inconclusive result, with no extra run, no lost proposal and no fabricated verdict.
