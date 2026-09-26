# Using TypeSafe's Jev for evals in Datadog Agent Observability

- **URL:** https://www.datadoghq.com/blog/jev-evals-agent-observability
- **Type:** vendor blog
- **Author / org:** Fouad Wahabi (Software Engineering Lead), Alex Barksdale (Senior Software Engineer), Miguel Tulla Lizardi (Software Engineer), Datadog
- **Date:** 2026-09-24
- **Retrieved:** 2026-09-26 (local copy: raw/web/datadog-jev-evals-agent-observability.txt, extracted article text. Code blocks carry line-number artifacts from the HTML, which are cleaned in the quotes below.)
- **Cited by evidence:** Typed-decision tier displacing LLM calls on bounded classification / 2026-09-25 kaixin_tai ("Datadog agent observability runs online and offline evals with Jev as the judge"). Post text: "run cheap and fast online and offline evals with jev in datadog agent observability"
- **Relevance to a memory stack:** medium-high. The article gives concrete, reusable patterns for using a decision model as a judge. These patterns transfer directly to judging memory quality (grounded recall, missed recall, contradiction) online and offline.

## TL;DR
- One Jev rubric (5 questions: 3 Noul, 1 Choice, 1 Score) is sent in **one request per turn**. The same `judge()` function drives both online evals (live spans, scored out of band) and offline experiments.
- For Noul answers, submit the **raw probability** as the score and put pass/fail in `assessment`. A threshold change then becomes a query change, not a rescoring job.
- Keep composite verdicts, thresholds, arithmetic and dates **in code**, not in Jev questions.
- A Choice question never abstains, so add an explicit `unclear` option. Treat near-ties (none 0.46 vs partial_answer 0.42) as a trigger for human review.
- The article reports **no latency, cost or agreement numbers** beyond one sample response and a screenshot. It advises measuring agreement with humans and repeatability yourself.

## What it claims / describes
- Jev takes a state (a string or JSON object) plus typed questions, and returns typed answers with probabilities. "It never explains itself, and that constraint is the whole idea." Eval pipelines have been "paying generation prices for what amounts to a single bit."
- Question types:

| Question Type | Returned Signal | Example evaluation |
|---|---|---|
| Noul | Probability that a yes/no proposition is true | Are the reply's policy claims supported by the retrieved excerpts? |
| Choice | Selected category, probabilities for all categories, and confidence | What is the reply's main failure mode? |
| Score | A probability-weighted average of rubric levels, plus the level distribution and confidence | How severe is the potential customer impact? |

- "A Noul probability expresses uncertainty about a proposition; it does not measure how much of the reply is correct." "A confident answer can still be wrong."
- "Questions in the same request are evaluated independently against a shared state."
- **Test case:** a support agent for the fictional airline Vega Air answers from retrieved policy excerpts. The policy corpus has deliberate holes. A good reply either answers from the excerpts or says they don't cover the question and offers a human handoff. A bad reply invents policy (typically a fee).
- **Rubric (5 questions):** `grounded` (Noul), `failure_mode` (Choice), `answers_question` (Noul), `offers_handoff` (Noul), `customer_impact` (Score, levels 0 to 3). `instructions` can be a string or an object with keys `question`, `scope` and optionally `inspect`. `criteria` spells out each outcome.

Rubric code (verbatim, line numbers removed):
```python
from typesafe_sdk import Choice, Noul, NoulCriteria, TypeSafeClient

# Pinned rather than jev-latest: the thresholds below were calibrated against
# this exact version, and an alias moves when a release ships.
JEV_MODEL = "jev-1.13.0"

GROUNDED_THRESHOLD = 0.70

QUESTIONS = {
    "grounded": Noul(
        instructions={
            "question": (
                "Is every factual claim about Vega Air policy in `reply` stated in, or "
                "directly restated from, `policy_context`?"
            ),
            "inspect": "reply",
            "scope": [
                "Only policy claims count: fees, amounts, deadlines, weight limits, eligibility.",
                "Ignore greetings, apologies, and offers to hand off to a human agent.",
                "A reply that states no policy claims at all is grounded.",
            ],
        },
        criteria=NoulCriteria(
            true="Every policy claim in `reply` appears in `policy_context`.",
            false=(
                "At least one policy claim in `reply` is absent from `policy_context`, "
                "contradicts it, or changes a number, fee, or deadline."
            ),
        ),
    ),
    "failure_mode": Choice(
        instructions={
            "question": "What is the single biggest problem with `reply`?",
            "scope": (
                "Pick `none` when the reply is fine. Pick `unclear` only when the reply "
                "is too short or too garbled to judge."
            ),
        },
        criteria={
            "none": "The reply is accurate, on-policy, and useful.",
            "unsupported_claim": "The reply states a fee, rule, or number that is not in `policy_context`.",
            "missed_handoff": (
                "`policy_context` does not cover the question and the reply neither says so "
                "nor offers a human agent."
            ),
            "partial_answer": "The reply covers part of the question and silently drops the rest.",
            "unsafe_request": (
                "The reply complies with a request for personal data or something outside "
                "support scope."
            ),
            "unclear": "The reply is too short or too garbled to judge.",
        },
    ),
    # answers_question and offers_handoff are two more Nouls; customer_impact is a Score.
}
```
- "A Choice question always returns the option with the highest probability, so Jev never abstains. If an evaluation needs a way to say 'cannot judge this one,' that outcome has to exist in the criteria."

A real response (verbatim). The ticket asked about cancellation compensation, the policy covered only delays, and the agent declined and offered a handoff:
```json
{
  "model": "jev-1.13.0",
  "answers": {
    "grounded":         {"type": "noul", "noul": 0.63},
    "answers_question": {"type": "noul", "noul": 0.02},
    "offers_handoff":   {"type": "noul", "noul": 0.99},
    "failure_mode": {
      "type": "choice",
      "choice": "none",
      "confidence": 0.34,
      "probabilities": {
        "none": 0.46, "partial_answer": 0.42, "unsupported_claim": 0.11,
        "missed_handoff": 0.01, "unclear": 0.0, "unsafe_request": 0.0
      }
    },
    "customer_impact": {
      "type": "score",
      "score": 1.25,
      "confidence": 0.74,
      "probabilities": {"0": 0.01, "1": 0.76, "2": 0.21, "3": 0.02},
      "legend": {
        "0": "No harm. The customer gets what they need.",
        "1": "Mild friction. The customer must ask again or look elsewhere.",
        "2": "Real cost. The customer acts on wrong information or is stranded without a route forward.",
        "3": "Serious harm. The customer loses money, misses travel, or their privacy is breached."
      }
    }
  },
  "usage": {"input_tokens": 1181, "output_tokens": 139}
}
```
Composite verdict, kept in code:
```python
# Handled correctly means grounded, and either answered or routed to a human.
handled = grounded >= GROUNDED_THRESHOLD and (
    answered >= ANSWERED_THRESHOLD or handoff >= HANDOFF_THRESHOLD
)
```
The judge call:
```python
def judge(client, question, policy_context, reply, extra_questions=None):
    """One request, five answers, all scored in parallel against one state."""
    return client.system_one(
        state={"question": question, "policy_context": policy_context, "reply": reply},
        questions={**QUESTIONS, **(extra_questions or {})},
    )
```
- "Jev loses accuracy as the state fills with material the question doesn't need, so filter in code and send only what each question reads."
- "Jev reads dates as text and doesn't count reliably, so anything a parser can compute belongs in code."

**Online evals.** The traced app never imports Jev. A separate worker scores out of band, which also allows backfilling history. The app tags spans with a domain key (`turn_id`). The scorer joins on that tag via `LLMObs.submit_evaluation(span_with_tag_value={"tag_key": "turn_id", "tag_value": ...}, ml_app=..., timestamp_ms=turn["timestamp_ms"], **metric)`. Passing the turn's own `timestamp_ms` keeps reruns idempotent: rescoring updates the existing verdict.

**Metric mapping.** The four metric types are score, categorical, boolean and json.
- Noul: submit the raw probability as `score` and put pass/fail in `assessment`. Metric example: `{"label": "jev_grounded", "metric_type": "score", "value": round(v["grounded"], 4), "assessment": "pass" if v["grounded"] >= GROUNDED_THRESHOLD else "fail", "reasoning": f"P(grounded)={v['grounded']:.2f}, threshold={GROUNDED_THRESHOLD}", "tags": {"judge": "typesafe-jev", "judge_model": v["model"]}}`.
- Choice: submit the label as `categorical`, plus confidence as a separate `score`. "A wrong verdict and an uncertain verdict are different problems." Rising uncertainty can mean rubric drift.
- Tag every metric with `judge_model`, because `jev-latest` moves between releases.

**Offline experiments.** Ported naively, each evaluator would make its own request per row: "Six evaluators over ten rows would be sixty requests instead of ten." Instead, cache one Jev response per row. "Guard the dictionary, not the request": holding a lock across the network call would serialise `experiment.run(jobs=4)`. The evaluators are `JevNoul`, `JevFailureMode`, `JevCustomerImpact`, `JevHandledCorrectly` and `JevAgreesWithLabel`, plus the summary evaluator `JevHandledRate`. `JevAgreesWithLabel` adds a `BEHAVIOR_QUESTION` Choice and compares it with `context.expected_output`. This turns the experiment into a calibration check on both the agent and the judge. Rerun it when the rubric or the Jev version changes.

**Access and setup:** Jev is available directly or via OpenRouter or Vercel AI Gateway, with Python and JS SDKs and a TypeSafe agent skill. The Datadog side needs `ddtrace>=v4.5.0`. Repo: https://github.com/DataDog/llm-observability (`typesafe-jev/`), with notebooks 1-jev-rubric, 2-online-evals and 3-experiments. Environment variables: DD_API_KEY, DD_APPLICATION_KEY, DD_SITE, OPENAI_API_KEY, TYPESAFE_API_KEY.

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Tokens for one 5-question judgement | 1,181 input / 139 output | n/a | sample response | Single example |
| Requests per row (cached) | 1 instead of 6 | 6 (naive one per evaluator) | 6 evaluators x 10 rows = 10 vs 60 | |
| GROUNDED_THRESHOLD | 0.70 | | pinned to jev-1.13.0 | ANSWERED and HANDOFF thresholds not stated |
| jev_grounded pass rate (screenshot alt text) | 90% | | demo data | Toy dataset |
| Experiment summary cards (screenshot in the kaixin_tai post) | agrees_with_label 90% true; answers_question 0.528 avg; customer_impact 0.641 avg; failure_mode 90% none; grounded 0.911 avg; handled_correctly 90% true | | 10 records | Demo only, not a benchmark |
| Latency / cost / human agreement | not stated | | | The article recommends measuring these yourself |

## Mechanism details you could implement
- One multi-question request per item, against a minimal state of named fields (not the whole trace).
- Store probabilities, not booleans. Apply thresholds at query time.
- Store Choice confidence separately and alert on falling confidence as a sign of judge drift.
- Pin the model version, and log the returned model version on every score.
- Keep an explicit `unclear` option in Choice questions. Route near-ties to human review.
- Use an idempotent join key plus the original timestamp so backfills and rescoring overwrite rather than duplicate.
- Use a per-row cache with a lock on the dict only.

## Limitations, caveats, counter-evidence
- The demo covers 10 rows on a fictional dataset. There is no evidence of judge accuracy, speed or cost.
- The authors state that Jev "has known limitations". They say to measure agreement and repeatability on your own traffic.
- Jev is unreliable at counting and date arithmetic, and its accuracy degrades with irrelevant state.

## Takeaways for tuning a memory stack
- To evaluate recall quality, frame a rubric like this one: `grounded` (is the answer supported by the recalled memories?), `missed_recall` (a Choice failure mode), `stale_memory_used`, and so on. Use one request per turn, and score offline and online with the same `judge()`.
- Log raw probabilities, so you can retune memory-quality thresholds without rescoring.
- Keep the state minimal (query, recalled memories, answer), because irrelevant state lowers accuracy.
- Build a labelled calibration set (`agrees_with_label`) before trusting the judge for memory-quality regressions.

## Open questions
- What agreement rate with human reviewers, and what latency and cost per judgement, did Datadog observe?
- What are the ANSWERED_THRESHOLD and HANDOFF_THRESHOLD values?
- How repeatable is the output across calls (for self-consistency)?

---
