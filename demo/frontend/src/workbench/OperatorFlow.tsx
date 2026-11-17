import type { ReviewTicks } from "./reviewTicks";
import { sandboxGuidance } from "./results";
import { useEffect, useState, type ReactNode } from "react";
import type { Capabilities, Content, Draft } from "./types";
import { PackGraph } from "./PackGraph";
import type { ExplainScope } from "./ExplainProblem";

export const journey = [0, 1, 2, 3, 4, 5, 6];
export function nextTask(
  d: Draft,
  c: Content,
): { step: number; title: string; reason: string } {
  if (
    !c.scope.trim() ||
    c.data_policy === "undecided" ||
    !c.redaction_confirmed
  )
    return {
      step: 0,
      title: "Describe the tenant and confirm data handling",
      reason:
        "The agent needs a clear purpose and permission before using tenant material.",
    };
  if (d.proposal && !d.proposal_stale && !d.review?.pack_accepted && d.proposal.limitations.length)
    return c.data_policy === "local_only"
      ? {step: 2, title: "Review the saved concerns", reason: "You can inspect the saved proposal locally. Asking the agent or sending a revision requires permission in Tenant setup."}
      : {step: 2, title: "Review the agent’s open questions", reason: "Read the unresolved items in the pack review. Ask the agent to explain their business impact before deciding; its concerns are not confirmed engine failures."};
  if (
    !c.sources.length ||
    !c.sources.some((s) => s.kind === "schema") ||
    !c.sources.some((s) => s.kind === "samples")
  )
    return {
      step: 1,
      title: "Add the missing tenant evidence",
      reason:
        "Bring a process description, the event contract and a few example events. You can begin a conceptual draft before all inputs are available.",
    };
  if (d.pending_decisions || JSON.stringify(c.decisions) !== JSON.stringify(d.content.decisions))
    return {step: 2, title: "Apply your pending answers", reason: "The agent has not incorporated these answers yet. Apply them together, then review and rerun the examples."};
  const unanswered = d.proposal?.decisions.find(x => !c.decisions[x.id]);
  if (unanswered && !d.proposal_stale) return {
    step: 2, title: "Answer the missing-evidence question", reason: unanswered.question,
  };
  if (!d.proposal || d.proposal_stale || !d.proposal.pack)
    return {
      step: 2,
      title: d.proposal ? "Update the pack" : "Build the first pack",
      reason:
        "Ask the agent to turn the supplied evidence into a proposal you can review.",
    };
  if (
    ( !c.decisions.identity && !d.review?.confirmed_policies?.includes("identity")) ||
    (Object.values(d.proposal.pack?.types?.nodes || {}).some((node: any) => node.lifecycle) && !c.decisions.lifecycle && !d.review?.confirmed_policies?.includes("lifecycle")) ||
    d.proposal.decisions.some((x) => !c.decisions[x.id])
  )
    return {
      step: 2,
      title: "Answer the agent’s questions",
      reason:
        "Review and confirm the applicable identification and state-change rules below. These confirmations do not require another agent call.",
    };
  if (d.readiness.run.missing.includes("Revalidate after the engine changed"))
    return {
      step: 2,
      title: "Check the pack against the updated engine",
      reason:
        "The engine changed since this evidence was recorded. Revalidate the same pack, then rerun the examples; no new author request is needed.",
    };
  if (!d.validation?.passed)
    return {
      step: 2,
      title: "Resolve the pack checks",
      reason:
        "The engine has not validated this proposal. Inspect the errors before accepting it.",
    };
  if (
    !d.review?.pack_accepted ||
    d.review.accepted_facts.length !== d.proposal.facts.length ||
    d.review.rejected_facts?.length
  )
    return {
      step: 2,
      title: "Review the pack and its sources",
      reason:
        "Check the entities, identity rules, lifecycle and limitations together. Evidence is available alongside the pack.",
    };
  if (
    !c.questions.length ||
    c.questions.some((q) => !q.reviewed || (q.expectation_statement != null && !q.expectation_statement.trim())) ||
    !c.graph_reviewed ||
    !c.expected_nodes.length
  )
    return {
      step: 4,
      title: c.expected_nodes.length > 0 && !c.graph_reviewed
        ? "Confirm your saved graph selections"
        : "Choose what a correct result looks like",
      reason: c.expected_nodes.length > 0 && !c.graph_reviewed
        ? "Your selections are saved, but their review is not confirmed. Review them in Questions to answer, tick the graph review box and continue."
        : "Select expected answers and graph outcomes before running the test. The agent must not choose the pass criteria for you.",
    };
  if (!c.trust_reviewed) return {step: 0, title: "Review which sources this test trusts", reason: "Confirm the source-trust settings in Tenant setup before running examples. This does not grant production access."};
  if (!d.sandbox)
    return {
      step: 5,
      title: "Run the example events",
      reason:
        "Build an isolated graph and compare the actual results with your reviewed expectations.",
    };
  if (!d.sandbox.passed) return sandboxGuidance(d.sandbox);
  return {
    step: 6,
    title: d.approval
      ? "Approved package is ready for handoff"
      : "Review the evidence and approve",
    reason:
      "Approval freezes this artifact. It does not deploy or activate the tenant.",
  };
}

export function AuthorSession({
  draft,
  content,
  caps,
  busy,
  prompt,
  setPrompt,
  onAuthor,
  onCancel,
  explainFailure,
  requestReviewActive = false, onReviewRequest,
}: {
  draft: Draft;
  content: Content;
  caps: Capabilities;
  busy: boolean;
  prompt: string;
  setPrompt: (v: string) => void;
  onAuthor: () => void;
  onCancel: () => void;
  explainFailure?: ReactNode;
  requestReviewActive?: boolean; onReviewRequest?: () => void;
}) {
  const running = draft.job?.status === "running";
  const [elapsed, setElapsed] = useState(0);
  const start = [...draft.history]
    .reverse()
    .find((h) => h.action === "author_started")?.at;
  useEffect(() => {
    if (!running || !start) return;
    const tick = () =>
      setElapsed(
        Math.max(0, Math.floor((Date.now() - Date.parse(start)) / 1000)),
      );
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [running, start]);
  const allowed =
    caps.authoring &&
    content.data_policy === "provider_allowed" &&
    content.redaction_confirmed &&
    !!content.scope.trim() &&
    !!content.sources.length;
  return (
    <details
      className="wb-assistant-container"
      open={
        !draft.proposal ||
        !!draft.proposal_stale ||
        running ||
        (!!prompt && !requestReviewActive) ||
        !!draft.job?.error
      }
    >
      <summary>
        {draft.proposal
          ? "Ask the agent to change this pack"
          : "Build a pack with the agent"}
      </summary>
      <section
        className="wb-card wb-author-session"
        aria-label="Authoring agent"
      >
        <h2>
          {draft.proposal
            ? "Ask for a change"
            : "Build a pack from the tenant’s material"}
        </h2>
        <p>
          {draft.proposal
            ? "Explain the change you need. The agent will revise the proposal for your review."
            : "The agent reads your inputs, proposes entities and event mappings, and checks the proposal with Engram. You review the result before testing."}
        </p>
        <div className="wb-author-context">
          Using {content.sources.length} sources · {content.questions.length}{" "}
          test questions · {caps.model ? "Agent available" : "Agent not configured"}
        </div>
        {running ? (
          <div role="status" className="wb-job">
            <strong>
              {draft.job?.kind === "author"
                ? "Preparing and validating a proposal"
                : "Running the isolated test"}
            </strong>
            <p>
              {elapsed}s elapsed. {draft.job?.attempt
                ? `Attempt ${draft.job.attempt} of at most 3. `
                : "Authoring may include up to three validation-and-repair attempts. "}
              No changes go live.
            </p>
            <button className="wb-secondary" onClick={onCancel} disabled={busy}>
              Cancel task
            </button>
          </div>
        ) : (
          <>
            {draft.job?.error && (
              <p role="alert" className="wb-error">
                The task did not finish: {draft.job.error} Your saved inputs are
                retained.
                {draft.proposal && (
                  draft.proposal_stale || draft.pending_decisions
                    ? " Your previous pack is retained, but changed inputs or pending answers still need to be applied."
                    : " Your previous pack and its existing checks are retained. You can continue with that pack or retry your request."
                )}
              </p>
            )}
            {draft.job?.kind === "author" && draft.job?.status === "failed" && explainFailure}
            {requestReviewActive ? <p>Your request is beside the review item. <button type="button" className="wb-text" onClick={onReviewRequest}>Review or clear that request</button></p> : <><label>
              {draft.proposal
                ? "What should change?"
                : "Anything the agent should focus on? (optional)"}
              <textarea
                id="workbench-revision-request"
                rows={10}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={
                  draft.proposal
                    ? "For example: keep the account-specific services separate. Explain any unsupported requirement."
                    : "For example: explain how repeated incident numbers stay separate across accounts."
                }
              />
            </label>
            {!!prompt.trim() && <details><summary>Read the full prepared request</summary><p style={{whiteSpace: "pre-wrap", overflowWrap: "anywhere"}}>{prompt}</p></details>}
            <button onClick={onAuthor} disabled={busy || !allowed}>
              {draft.proposal ? "Send changes to the agent" : "Build the pack"}
            </button>
            </>}
            {!allowed && (
              <p className="wb-muted">
                To use the agent, complete tenant scope, provider
                permission and data review, add at least one source, and
                configure the agent.
              </p>
            )}
          </>
        )}
        {!!draft.author_messages?.length && (
          <details>
            <summary>
              Conversation history ·{" "}
              {
                draft.author_messages.filter((m) => m.role === "operator")
                  .length
              }{" "}
              requests
            </summary>
            {draft.author_messages.map((m, i) => (
              <article className="wb-message" key={i}>
                <strong>
                  {m.role === "operator" ? "Operator" : "Agent"}
                  {m.status ? ` · ${m.status}` : ""}
                </strong>
                <p>{m.text}</p>
              </article>
            ))}
          </details>
        )}
      </section>
    </details>
  );
}

export function ModelReview({
  draft,
  content,
  busy,
  dirty,
  onDecision,
  onAccept,
  onReject,
  onValidate,
  onApplyAnswers,
  onAddMaterial,
  onKeepRemoved,
  reviewTicks,
  onReviewTicks,
  explain,
}: {
  draft: Draft;
  content: Content;
  busy: boolean;
  dirty: boolean;
  onDecision: (id: string, value: string) => void;
  onAccept: (acceptedRemovals: string[], acceptedChanges: string[], confirmedPolicies: string[]) => void;
  onApplyAnswers: () => void;
  onAddMaterial: () => void;
  onKeepRemoved: () => void;
  reviewTicks: ReviewTicks;
  onReviewTicks: (ticks: ReviewTicks) => void;
  explain?: (scope: ExplainScope, index: number) => ReactNode;
  onReject: (id: string) => void;
  onValidate: () => void;
}) {
  const proposal = draft.proposal;
  const pack = proposal?.pack;
  const [questionTarget, setQuestionTarget] = useState("pack:0");
  useEffect(() => setQuestionTarget("pack:0"), [draft.id, JSON.stringify(pack)]);
  const removals = proposal?.repair_removals || [];
  const changes = draft.proposal_changes || [];
  const acceptedChanges = reviewTicks.changes;
  const acceptedRemovals = reviewTicks.removals;
  const confirmedPolicies = reviewTicks.policies;
  const setAcceptedChanges = (update: (values: string[]) => string[]) => onReviewTicks({...reviewTicks, changes: update(acceptedChanges)});
  const setAcceptedRemovals = (update: string[] | ((values: string[]) => string[])) => onReviewTicks({...reviewTicks, removals: typeof update === "function" ? update(acceptedRemovals) : update});
  const setConfirmedPolicies = (update: (values: string[]) => string[]) => onReviewTicks({...reviewTicks, policies: update(confirmedPolicies)});
  const unapplied = !!draft.pending_decisions || JSON.stringify(content.decisions) !== JSON.stringify(draft.content.decisions);
  const decisions = proposal?.decisions || [];
  const policies = [
    {id: "identity", label: "I checked the fields that identify each entity in this pack."},
    ...(Object.values(pack?.types?.nodes || {}).some((node: any) => node.lifecycle)
      ? [{id: "lifecycle", label: "I checked the states, transitions and update rules in this pack."}]
      : []),
  ];
  const policiesReady = policies.every(policy => !!content.decisions[policy.id] || confirmedPolicies.includes(policy.id));
  const pending = decisions.filter((d) => !content.decisions[d.id]);
  const disabled =
    busy || dirty || unapplied || draft.proposal_stale || draft.job?.status === "running";
  return (
    <>
      <section className="wb-card">
        <h2>
          {proposal ? "What the agent understood" : "The pack will appear here"}
        </h2>
        {!!proposal?.limitations.length && (
          <div className="wb-warning">
            <strong>Review these items first</strong>
            {!!decisions.length && <p>Answer the <a href="#recorded-decisions">recorded questions below</a>. If a fact is unknown, leave it blank and return with supporting material.</p>}
            <ul>
              {proposal.limitations.map((text, i) => (
                <li key={i}>
                  <details>
                    <summary>{text.split(/\. /)[0]}</summary>
                    <p>{text}</p>
                  </details>
                  {explain?.("limitation", i)}
                </li>
              ))}
            </ul>
          </div>
        )}

        {proposal ? (
          <>
            <h3>Pack overview</h3>
            <p>{proposal.summary}</p>
            {pack && <details><summary>Technical details · identifiers and states</summary>{Object.entries(pack.types?.nodes || {}).map(([name, def]: any) => (
              <p key={name}>{name} is identified by {(def.key || []).join(" and ")}.
                {def.lifecycle ? ` It starts ${def.lifecycle.initial}; its states are ${(def.lifecycle.states || []).join(", ")}.` : ""}
              </p>
            ))}</details>}
          </>
        ) : (
          <p>
            Add evidence and ask the agent to build a first proposal. No
            engine vocabulary is required to start.
          </p>
        )}
        {draft.job?.status === "cancelled" && <p role="status">The agent was cancelled. Your saved inputs and previous proposal are retained.</p>}
        {draft.proposal_stale && (
          <p className="wb-warning">
            This is an earlier proposal. Finish or retry the agent’s update before
            accepting it.
          </p>
        )}
        {pack && (
          <>
            <PackGraph
              nodes={Object.entries(pack.types?.nodes || {}).map(
                ([name, def]: any) => ({
                  id: name,
                  type: name,
                  properties: def,
                }),
              )}
              edges={Object.entries(pack.types?.edges || {}).flatMap(
                ([name, def]: any) =>
                  (def.from || []).flatMap((source: string) =>
                    (def.to || []).map((target: string) => ({
                      source,
                      type: name,
                      target,
                    })),
                  ),
              )}
              mode="schema"
            />
            <section aria-label="Ask about this pack">
              <h3>Ask about this pack</h3>
              <p>Understand a record, a relationship or the whole pack. Asking does not change it.</p>
              <label>What would you like to understand?
                <select aria-label="What would you like to understand?" id="workbench-pack-question-target" value={questionTarget} onChange={event => setQuestionTarget(event.target.value)}>
                  <option value="pack:0">The whole pack</option>
                  {Object.keys(pack.types?.nodes || {}).sort().map((name, index) => <option key={`node:${name}`} value={`node:${index}`}>Record — {name}</option>)}
                  {Object.keys(pack.types?.edges || {}).sort().map((name, index) => <option key={`edge:${name}`} value={`edge:${index}`}>Relationship — {name.split("_").join(" ").toLowerCase()}</option>)}
                </select>
              </label>
              {explain?.(questionTarget.split(":")[0] as ExplainScope, Number(questionTarget.split(":")[1]))}
            </section>
          </>
        )}
        {pack && Object.keys(pack.types?.edges || {}).map(name => {
          const path = `/types/edges/${name.replace(/~/g, "~0").replace(/\//g, "~1")}`;
          const support = proposal?.facts.filter(f => f.pack_paths?.some(p => p === path || p.startsWith(path + "/"))) || [];
          return <details key={name}><summary>Check the evidence for {name.split("_").join(" ").toLowerCase()}</summary>
            <p>A citation is a link to evidence, not proof that this relationship is correct. Check the meaning against your domain rules.</p>
            {support.length ? support.map(f => <div key={f.id}><p>{f.explanation}</p>
              {f.citations.map((c, i) => <blockquote key={i}>{c.quote}</blockquote>)}
              {f.instruction_quote && <blockquote>{f.instruction_quote}</blockquote>}
              {f.decision_ids?.map(id => <p key={id}>{content.decisions[id]}</p>)}
            </div>) : <p>No supporting statement is linked. Resolve this before accepting the pack.</p>}
          </details>;
        })}
        {!!proposal?.facts.length && (
          <details>
            <summary>
              Where this came from · {proposal.facts.length} statements with
              sources or assumptions
            </summary>
            {proposal.facts.map((f) => (
              <article className="wb-fact" key={f.id}>
                <strong>{f.concept}</strong>{" "}
                <span className="wb-pill">
                  {f.basis === "source"
                    ? "From a source"
                    : f.basis === "operator"
                      ? "Operator decision"
                      : "Assumption to check"}
                </span>
                <p>{f.explanation}</p>
                {!!f.pack_paths?.length ? <p>Applies to: {f.pack_paths.map(path => path.slice(1).split("/").join(" → ")).join("; ")}</p>
                  : <p className="wb-muted">No specific pack rule is linked to this statement. Check the rule before accepting it.</p>}
                {f.trusted_producers != null && <p><strong>Reviewed trust settings:</strong> {f.trusted_producers.length ? f.trusted_producers.join(", ") : "No producers marked as trusted"}</p>}
                {f.instruction_quote && <p><strong>{content.instruction.includes(f.instruction_quote) ? "Your revision request:" : "From an earlier request:"}</strong> {f.instruction_quote}</p>}
                {f.decision_ids?.map(id => <p key={id}><strong>Recorded decision:</strong> {content.decisions[id]}</p>)}
                {f.citations.map((c, i) => (
                  <blockquote key={i}>
                    <q>{c.quote}</q>
                    <cite>
                      {content.sources.find((s) => s.id === c.source_id)?.name}
                    </cite>
                  </blockquote>
                ))}
                <button
                  className="wb-text"
                  disabled={disabled}
                  onClick={() => onReject(f.id)}
                >
                  {draft.review?.rejected_facts?.includes(f.id)
                    ? "Rejected — undo"
                    : "This is wrong — request a correction"}
                </button>
              </article>
            ))}
          </details>
        )}
      </section>
      <section className="wb-card" aria-label="Decide and accept">
        <h2>Decide and accept</h2>
        {proposal && !pending.length && <p>No additional recorded decisions are waiting. Items above may still need your input; this does not mean the pack is ready.</p>}
        {proposal && <h3 id="recorded-decisions" tabIndex={-1}>Recorded decisions · {pending.length} awaiting your answer</h3>}
        {pack && <fieldset><legend>Confirm this pack</legend>
          <p>These confirmations review the displayed pack. They do not request another assistant run. To change a rule, ask for a revision.</p>
          {policies.map(policy => <label className="wb-checkbox" key={policy.id}>
            <input type="checkbox" disabled={!!disabled || !!content.decisions[policy.id]}
              checked={!!content.decisions[policy.id] || confirmedPolicies.includes(policy.id)}
              onChange={e => setConfirmedPolicies(values => e.target.checked ? [...values, policy.id] : values.filter(v => v !== policy.id))} />
            {policy.label}{content.decisions[policy.id] && <small>Recorded policy: {content.decisions[policy.id]}</small>}
          </label>)}
        </fieldset>}
        {!!decisions.length && <button type="button" className="wb-secondary" onClick={onAddMaterial}>Add supporting material</button>}
        {decisions.map((d, index) => (
          <div key={d.id}><label>
            {d.question}<small>{d.effect}</small>
            <textarea rows={2} value={content.decisions[d.id] || ""}
              onChange={(e) => onDecision(d.id, e.target.value)} />
          </label>{explain?.("decision", index)}</div>
        ))}
        {unapplied && <p role="status">Your answers are pending. Apply them together before accepting or testing this pack.</p>}
        {(decisions.length > 0 || unapplied) && <p id="apply-answers-reason" role="status">{busy || draft.job?.status === "running" ? "Wait for the current task to finish before applying answers." : pending.length ? `Answer all recorded questions before applying them. Still unanswered: ${pending.length} recorded questions. If you do not know, leave the question blank. You can return with more information; nothing is sent or approved.` : !unapplied ? "There are no new answers to apply." : "All questions have answers. Apply them together to request a revised proposal; this does not approve it."}</p>}
        {(decisions.length > 0 || unapplied) && <button aria-describedby="apply-answers-reason" disabled={busy || draft.job?.status === "running" || !unapplied || !!pending.length}
          onClick={onApplyAnswers}>Apply answers with the agent</button>}
        {!!changes.length && <section className="wb-warning">
          <h3>What changed in this pack</h3>
          <p>Compare this proposal with the previous pack. Review the changes in each group before accepting. Removals still need separate confirmation. Nothing has changed in production.</p>
          {[...new Set(changes.map(change => change.category))].map(category => {
            const group = changes.filter(change => change.category === category);
            const ids = group.map(change => change.id);
            return <article key={category}>
              <h4>{category} · {group.length} changes</h4>
              {group.map(change => <div key={change.id}>
                <p>{change.summary}</p>
                <details><summary>Inspect the changed rule</summary>
                  <p>{change.path.join(" → ")} ({change.kind})</p>
                  <strong>Before</strong><pre>{JSON.stringify(change.before, null, 2)}</pre>
                  <strong>Proposed</strong><pre>{JSON.stringify(change.after, null, 2)}</pre>
                </details>
              </div>)}
              <label className="wb-checkbox"><input type="checkbox" disabled={!!disabled}
                checked={ids.every(id => acceptedChanges.includes(id))}
                onChange={event => setAcceptedChanges(current => event.target.checked
                  ? [...new Set([...current, ...ids])]
                  : current.filter(id => !ids.includes(id)))} />
                I reviewed these {group.length} {category.toLowerCase()} changes
              </label>
            </article>;
          })}
        </section>}
        {!!removals.length && <section className="wb-warning">
          <h3>The agent proposed removing data</h3>
          <p>These items existed in an earlier proposal or repair attempt and are absent now. Nothing has changed in production. Keep them by requesting a revision, or explicitly accept each omission.</p>
          {removals.map(item => <label className="wb-checkbox" key={item}>
            <input type="checkbox" checked={acceptedRemovals.includes(item)} disabled={!!disabled}
              onChange={e => setAcceptedRemovals(items => e.target.checked ? [...items, item] : items.filter(x => x !== item))} />
            I accept removing {item}
          </label>)}
          <button className="wb-secondary" onClick={() => {
            setAcceptedRemovals([]);
            onKeepRemoved();
          }}>Keep this data — prepare a revision request</button>
        </section>}
        {pack && (
          <div className="wb-model-checks">
            <strong>
              {!draft.validation
                ? "No current pack check result — check again before accepting"
                : draft.validation.passed
                  ? "Engram’s pack checks passed"
                  : "Engram’s pack checks need attention"}
            </strong>
            {draft.validation?.problems?.length ? (
              <ul>
                {draft.validation.problems.map((p, i) => (
                  <li key={i}>{p}{explain?.("problem", i)}</li>
                ))}
              </ul>
            ) : null}
            <button
              className="wb-secondary"
              disabled={disabled}
              onClick={onValidate}
            >
              Check this pack with Engram
            </button>
          </div>
        )}
        {pack && (
          <div className="wb-model-accept">
            <p>
              Accepting confirms you reviewed the pack, recorded decisions,
              supporting evidence and limitations. It does not approve
              deployment.
            </p>
            <button
              disabled={
                disabled ||
                !policiesReady || !!pending.length || changes.some(change => !acceptedChanges.includes(change.id)) || removals.some(item => !acceptedRemovals.includes(item)) ||
                !draft.validation?.passed ||
                !!draft.review?.rejected_facts?.length ||
                (!!draft.review?.pack_accepted &&
                  draft.review.accepted_facts.length === proposal?.facts.length)
              }
              onClick={() => onAccept(acceptedRemovals, acceptedChanges, confirmedPolicies)}
            >
              {draft.review?.pack_accepted
                ? "Pack accepted for testing"
                : "I reviewed this pack — accept for testing"}
            </button>
            {!!draft.review?.rejected_facts?.length && (
              <p>
                Rejected statements must be resolved in a revised proposal
                first.
              </p>
            )}
          </div>
        )}
      </section>
    </>
  );
}
