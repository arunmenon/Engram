# Building Custom Agent Harness with Jev

- **URL:** https://medium.com/@bijit211987/building-custom-agent-harness-with-jev-59a240bfc663
- **Type:** builder writeup (Medium)
- **Author / org:** Bijit Ghosh (@bijitghosh21 on X, @bijit211987 on Medium)
- **Date:** 2026-09-24 (RSS pubDate Thu, 24 Sep 2026 13:15:56 GMT)
- **Retrieved:** 2026-09-26. A direct fetch of the Medium page returned HTTP 403, so the full article body was taken from the author's Medium RSS feed (https://medium.com/feed/@bijit211987). Local copy: raw/web/medium-bijit-jev-agent-harness.txt. The RSS body appears complete (it runs through the final section "Expand Autonomy Through Evaluation"). The lead image (https://cdn-images-1.medium.com/max/1024/1*RCNeCEJ265Edw4Bwa7yb4A.png) was not viewed.
- **Cited by evidence:** Decision models as the memory control plane / 2026-09-25 bijitghosh21 ("Builder writeup puts one Jev decision layer across routing, memory, retrieval, tool execution and loop control in an agent harness"). The citing post says "Step by step architecture, code, diagrams, and tradeoffs."
- **Relevance to a memory stack:** medium-low. The article is about action gating and verification. **It does not describe memory or retrieval decisions.** The only state component is "a durable state store [that] tracks progress, approvals, and completed operations." The citing post's mention of "memory, retrieval" is not borne out by the article text.

## TL;DR
- The harness wraps Claude or Codex (behind a runtime adapter). Jev supplies "focused judgments for model routing, proposed actions, and answer verification."
- The loop is Propose, validate, judge, authorize, execute, verify, bounded by time, cost and step limits.
- Hard permissions are enforced in code before Jev is called. Jev Noul outputs for scope violation, security regression and data loss are combined by **max** (not average) and mapped to BLOCK / REVIEW / ALLOW through two thresholds.
- Approvals are bound to the exact operation and the resource version. Action states are persisted so retries after timeouts do not repeat side effects.
- Rollout starts in observation mode (shadow decisions compared with reviewed outcomes). The key metric is total cost per verified completion.
- **No numbers are reported**: no latency, cost, accuracy or threshold values.

## What it claims / describes
**Motivating failure:** "Update the service configuration and fix the failing tests." An agent may overwrite an unrelated setting or weaken an assertion so the test passes. "Every tool call can succeed while the overall task fails."

**Runtime adapter:** Claude and Codex sit behind an adapter that translates events, task state and approval requests into a common internal representation. Policies stay separate from the runtime. The critical requirement is interception: "I verify which operations each integration can block before execution. For tools I control, I enforce the policy inside the tool service. Observing an action after it runs is too late to prevent it."

**Five components:**
1. Runtime adapter (interaction with the agent).
2. Durable state store (progress, approvals, completed operations).
3. Jev client (requests judgments "with deadlines and response validation").
4. Policy engine (converts judgments into decisions).
5. Tool executor (checks permissions, performs approved actions).

Loop: "Propose → validate → judge → authorize → execute → verify." Each step produces a record the next step inspects. "This structure lets me test policy decisions without making live model calls."

**Jev questions for the configuration task (verbatim):**
- "Does the proposed diff extend beyond the requested change?"
- "Could this operation destroy existing work?"
- "Does the supplied evidence support modifying this file?"

The state provided is the original request, the proposed diff, the relevant policy and target metadata. "A tool name such as write_file cannot answer those questions." Independent questions about the same state share one request. If a judgment needs more evidence, the workflow retrieves it first. (This is the only "retrieval" in the article: evidence fetch before a judgment.)

**Policy pseudocode (verbatim):**
```
# Enforce permissions in code.
if permission_denied:
    BLOCK

# Missing or invalid judgments cannot authorize execution.
if judgment_unavailable:
    REVIEW

# Jev supplies separate signals; code applies policy.
highest_violation_probability = max(
    scope_violation,
    security_regression,
    unintended_data_loss
)

# A strong violation takes precedence over missing evidence.
if highest_violation_probability >= block_threshold:
    BLOCK

# Pause when evidence or the evaluated resource has changed.
if required_evidence_missing or resource_version_changed:
    REVIEW

if highest_violation_probability >= review_threshold:
    REVIEW

ALLOW
```
An allowed action still passes a final permission and resource-version check immediately before execution. The author tunes thresholds "using reviewed examples, weighing both missed violations and unnecessary interruptions."

On semantics: "A Noul value estimates how likely a specific condition is to be true ... It does not measure how much harm that change could cause. Account for severity separately in the policy." And: "Taking the highest violation probability prevents a strong warning from being averaged away. It does not calculate the overall probability of harm."

**Approvals:** bound to target, arguments, proposed diff, expected effect and the resource version reviewed. If the resource changed while approval was pending, the diff is regenerated and reassessed. Alternate execution paths must be covered too: "Restricting a file-writing tool accomplishes little if an unrestricted shell can modify the same file."

**Routing:** Jev judges bounded characteristics such as scope and complexity. The policy combines them with budget, latency and required capabilities. Route at task boundaries, because switching models mid-run affects context transfer and caching cost. The metric is "total cost per verified completion, including retries, tool calls, and human review."

**Recovery:** "A timeout creates uncertainty. It does not prove that an operation failed." Action states (proposed, approved, started, completed) are persisted. The recorded status and the resulting resource are checked before any retry. External writes use idempotency keys. Jev calls have deadlines and bounded retries. If a judgment remains unavailable, the workflow pauses or follows a predefined fallback. Cancellation stops new actions and keeps a record of changes already made.

**Verification:** Jev assesses whether the diff matches the request and whether the final explanation follows from the evidence (the author references TypeSafe's citation-checking example). This is combined with direct checks: exit codes, diffs, artifact existence. "Passing tests are insufficient if the agent weakened their assertions."

**Autonomy expansion:** start in observation mode, recording what Jev and the policy would allow, block or escalate, and compare with reviewed outcomes. Measure missed risks, unnecessary blocks, review volume, completion quality, latency and cost. The eval set covers malicious repo instructions, stale approvals, missing evidence, interrupted writes and duplicate executions. Logs preserve model versions, policy versions, action ids and outcomes while protecting sensitive content.

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| (none) | not stated | | | The article reports no quantitative results, thresholds, latencies or costs |

## Mechanism details you could implement
- A max-of-violations policy with two thresholds (`block_threshold` > `review_threshold`) over independent Noul signals. Missing judgment leads to REVIEW, never ALLOW (fail closed).
- Multiple Noul questions batched in one request against a shared state (request, diff, policy, target metadata).
- A persisted action state machine (proposed, approved, started, completed) with idempotency keys and resource-version binding on approvals.
- Shadow or observation mode before enabling enforcement.
- (inference, applying this to memory) The same pattern could gate memory writes: Nouls such as "does this memory contradict an existing one?" or "is this a one-off?", combined by max and routed to BLOCK / REVIEW / ALLOW, with the memory record's version bound at approval time. The article does not describe this.

## Limitations, caveats, counter-evidence
- The article contains no empirical results. It is a design essay.
- The citing claim (a decision layer across "memory, retrieval") overstates the text. Memory appears only as a durable state store for run state, and retrieval appears only as fetching extra evidence for a judgment.
- Threshold values are not given.
- The lead diagram was not reviewed.

## Takeaways for tuning a memory stack
- Treat decision-model outputs as signals and keep policy (thresholds, severity, composites) in code. Datadog's eval guidance makes the same point.
- Combine several risk signals by max rather than average, so one strong warning is not diluted.
- Fail closed to REVIEW when the decision model is unavailable. For memory writes, this means queueing the write rather than silently writing or dropping it (inference).
- Bind consolidation or overwrite approvals to a record version to avoid lost updates (inference).
- Measure cost per verified completion, not cost per call.

## Open questions
- What thresholds did the author actually use, and what were the observation-mode results?
- Did the author apply the pattern to memory reads or writes anywhere? The citing post suggests so; the article does not show it.

---
