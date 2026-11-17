import { useEffect, useState } from "react";
import type { Draft } from "./types";

export function JourneyAuthor({
  draft,
  busy,
  model,
  act,
  suggestion,
}: {
  suggestion?: string;
  draft: Draft;
  busy: boolean;
  model: string | null;
  act: (endpoint: string, body?: Record<string, unknown>) => void;
}) {
  const [goal, setGoal] = useState(draft.journey_brief?.goal || "");
  const [specification, setSpecification] = useState(
    draft.journey_brief?.specification || "",
  );
  const [permission, setPermission] = useState(false);
  const [decisions, setDecisions] = useState(draft.journey_decisions || "");
  const [outlineReviewed, setOutlineReviewed] = useState(false);
  const [answersReviewed, setAnswersReviewed] = useState(false);
  const outline = draft.journey_outline;
  const proposal = draft.journey_proposal;
  const [acceptedChecks, setAcceptedChecks] = useState<string[]>([]);
  // Polls deserialize a new object even when the proposal is unchanged.
  // Bind acknowledgement to its content and draft revision, not object identity.
  const proposalContent = JSON.stringify(proposal ?? null);
  useEffect(() => {
    setAcceptedChecks([]);
    setAnswersReviewed(false);
  }, [proposalContent, draft.id, draft.revision]);
  const checkReview = (c: any) => <label><input type="checkbox"
    checked={acceptedChecks.includes(c.id)}
    onChange={e => setAcceptedChecks(ids => e.target.checked ? [...ids, c.id] : ids.filter(id => id !== c.id))}
  /> I checked this expected outcome against the domain rules: {c.description}</label>;
  useEffect(() => {
    if (!suggestion) return;
    setGoal((current: string) => current ? `${current}\n\nAlso cover: ${suggestion}` : suggestion);
    setOutlineReviewed(false); setAnswersReviewed(false);
    requestAnimationFrame(() => document.getElementById("story-goal")?.focus());
  }, [suggestion]);
  const sameBrief =
    goal === draft.journey_brief?.goal &&
    specification === draft.journey_brief?.specification;
  return (
    <section className="wb-card">
      <details open={!!suggestion || !draft.journey.expectations_reviewed || undefined}>
        <summary>Create a new story with the agent</summary>
        <p>
          Start with a business situation and its rules. The agent proposes
          a plan first, then creates sample events and expected results. Your
          existing journey stays intact.
        </p>
        {!model && (
          <p>
            The authoring agent is not configured. Prepared journeys can still run.
          </p>
        )}
        <fieldset disabled={busy || !model}>
          <label>
            What situation should we test?
            <textarea
              id="story-goal"
              value={goal}
              onChange={(e) => {
                setGoal(e.target.value);
                setOutlineReviewed(false);
                setAnswersReviewed(false);
              }}
              placeholder="Example: create a record, change its state, then retry the last event without changing the result."
            />
          </label>
          <label>
            Domain rules and expected behaviour
            <textarea
              value={specification}
              onChange={(e) => {
                setSpecification(e.target.value);
                setOutlineReviewed(false);
                setAnswersReviewed(false);
              }}
              placeholder="Paste a short specification. State what must happen and what must never happen."
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={permission}
              onChange={(e) => setPermission(e.target.checked)}
            />{" "}
            I reviewed these inputs for sensitive data and allow this brief, the
            saved story, coverage notes and pinned pack to be sent to the agent’s external service.
          </label>
          <button
            disabled={
              !permission || goal.length < 10 || specification.length < 10
            }
            onClick={() => {
              setOutlineReviewed(false);
              setAnswersReviewed(false);
              act("journey-outline", {
                goal,
                specification,
                provider_allowed: permission,
              });
            }}
          >
            Propose journey outline
          </button>
          {outline && (
            <>
              <h3>{outline.title}</h3>
              <p>{outline.story}</p>
              <ol>
                {outline.steps.map((s: string, i: number) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
              <h3>Assumptions to review</h3>
              {outline.assumptions.length ? (
                <ul>
                  {outline.assumptions.map((s: string, i: number) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              ) : (
                <p>
                  No assumptions flagged by the agent. Review the plan
                  against your rules.
                </p>
              )}
              {outline.questions.length > 0 && (
                <>
                  <h3>Decisions needed</h3>
                  <ul>
                    {outline.questions.map((s: string, i: number) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </>
              )}
              <details>
                <summary>Grounding sources</summary>
                <ul>
                  {outline.sources.map((s: string) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </details>
              <label>
                Decisions and corrections
                <textarea
                  value={decisions}
                  onChange={(e) => {
                    setDecisions(e.target.value);
                    setOutlineReviewed(false);
                    setAnswersReviewed(false);
                  }}
                  placeholder="Resolve the questions and confirm or correct the assumptions."
                />
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={outlineReviewed}
                  onChange={(e) => setOutlineReviewed(e.target.checked)}
                />{" "}
                I reviewed this outline and resolved its consequential
                assumptions.
              </label>
              {!sameBrief && (
                <p>
                  The brief has changed. Request a new outline before generating
                  events.
                </p>
              )}
              <button
                disabled={
                  !outlineReviewed || !sameBrief || decisions.length < 10
                }
                onClick={() => {
                  setAnswersReviewed(false);
                  act("journey-generate", {
                    decisions,
                    outline_reviewed: true,
                  });
                }}
              >
                Generate events and expected results
              </button>
            </>
          )}
          {proposal && (
            <>
              <h3>Review the generated variant</h3>
              <p>
                {proposal.title} · {proposal.events.length} events ·{" "}
                {proposal.checks.length} checks
              </p>
              <p>
                These are proposed expectations, not observed results. Verify
                them against your domain rules before running.
              </p>
              {(!sameBrief || decisions !== draft.journey_decisions) && (
                <p role="status">Your inputs have changed. Generate a new proposal before saving.</p>
              )}
              {proposal.events.map((e: any, i: number) => (
                <details key={e.id}>
                  <summary>
                    {i + 1}. {e.title}
                  </summary>
                  <pre>{JSON.stringify(e.request, null, 2)}</pre>
                  {proposal.checks
                    .filter((c: any) => c.after_step === i)
                    .map((c: any) => (
                      <div key={c.id}>
                        <strong>{c.description}</strong>
                        <pre>{JSON.stringify(c.expected, null, 2)}</pre>
                        {checkReview(c)}
                      </div>
                    ))}
                </details>
              ))}
              <details>
                <summary>Final graph and question expectations</summary>
                {proposal.checks
                  .filter((c: any) => c.after_step == null)
                  .map((c: any) => (
                    <div key={c.id}>
                      <strong>{c.description}</strong>
                      <pre>{JSON.stringify(c.expected, null, 2)}</pre>
                        {checkReview(c)}
                    </div>
                  ))}
              </details>
              <label>
                <input
                  type="checkbox"
                  checked={answersReviewed}
                  onChange={(e) => setAnswersReviewed(e.target.checked)}
                />{" "}
                I reviewed the generated events and expected outcomes
                independently of any run.
              </label>
              <button
                disabled={!answersReviewed || acceptedChecks.length !== proposal.checks.length || !sameBrief || decisions !== draft.journey_decisions}
                onClick={() => act("journey-accept", {accepted_checks: acceptedChecks})}
              >
                Save reviewed variant as a new workspace
              </button>
            </>
          )}
        </fieldset>
      </details>
    </section>
  );
}
