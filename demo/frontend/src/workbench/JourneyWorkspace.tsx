import { CheckExplanation } from "./CheckExplanation";
import type { ExplainResult } from "./ExplainProblem";
import { explainCheck } from "./results";
import { JourneyAuthor } from "./JourneyAuthor";
import { useState } from "react";
import { PackGraph } from "./PackGraph";
import type { Draft } from "./types";

export function JourneyWorkspace({
  draft,
  busy,
  run,
  cancel,
  model,
  backend,
  act,
  askCheck,
  explaining,
  allowExplanations,
}: {
  explaining: boolean;
  askCheck: (index: number, question: string, signal: AbortSignal) => Promise<ExplainResult>;
  allowExplanations: () => void;
  draft: Draft;
  busy: boolean;
  run: () => void;
  cancel: () => void;
  model: string | null;
  backend: string;
  act: (endpoint: string, body?: Record<string, unknown>) => void;
}) {
  const [step, setStep] = useState(0);
  const [failuresOnly, setFailuresOnly] = useState(true);
  const [coverageFilter, setCoverageFilter] = useState("gaps");
  const [coverageLimit, setCoverageLimit] = useState(8);
  const [coverageSearch, setCoverageSearch] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [consent, setConsent] = useState(false);
  const inspection = draft.story_inspection;
  const coverageLabels: Record<string, string> = {no_check: "No check", defined: "Defined · not executed", executed: "Executed · inspect outcome", passing: "Passing check", stale: "Stale result", needs_review: "Review assertion strength"};
  const coverageRows = (inspection?.rows || []).filter(row => (coverageFilter === "all" || row.status !== "passing") && `${row.label} ${row.kind}`.toLowerCase().includes(coverageSearch.toLowerCase()));
  const allowed = draft.content.data_policy === "provider_allowed" && draft.content.redaction_confirmed;
  const journey = draft.journey;
  const graphFixture = journey.starting_state !== "empty";
  const result = draft.journey_result;
  const snapshot = result?.steps[step] || result?.initial_graph;
  const results = result?.checks || [];
  const counts = (status: string) =>
    results.filter((c: any) => c.status === status).length;
  return (
    <>
      <div className="wb-heading">
        <div>
          <p className="wb-eyebrow">{(result?.pack_names || (draft.journey_pack_snapshot ? [draft.journey_pack_snapshot.primary_pack] : draft.content.existing_packs)).filter((name: string) => !["core", "memory", "user"].includes(name)).join(" + ") || "Selected pack"} · {graphFixture ? "ANSWER STORY" : !journey.expectations_reviewed ? "STORY DRAFT" : draft.journey_origin ? "REVIEWED STORY" : "PREPARED STORY"}</p>
          <h1>{journey.title}</h1>
          <p>{journey.story}</p>
        </div>
      </div>
      <section className="wb-card">
        <h2>Run this story</h2>
        <p>
          {journey.events.length} event deliveries · {journey.checks.length}{" "}
          checks · {graphFixture ? "starts with the saved test graph" : "starts with an empty graph"} {backend === "spanner" ? "on a dedicated Spanner sandbox database." : "in isolated memory."}
        </p>
        {graphFixture && <p>This loads {journey.starting_state.nodes.length} saved nodes and {journey.starting_state.edges.length} relationships. It verifies retrieval behaviour; it does not verify how these records were ingested or extracted.</p>}
        <p>
          The pack and expected outcomes are pinned. This run does not change
          the ontology or require an authoring agent.
        </p>
        {result?.packs && <p>Pack versions: {result.packs.map((p: {name: string; version: string}) => `${p.name} ${p.version}`).join(" · ")}</p>}
        {!journey.expectations_reviewed && <p>These sample events are a starting point. Use the agent below to propose a story, then review its expected outcomes before running it.</p>}
        <button disabled={busy || !journey.expectations_reviewed} onClick={run}>
          {result ? "Run story again" : "Run story"}
        </button>
        {draft.job?.status === "running" && (
          <>
            <p role="status">
              {draft.job.kind === "journey"
                ? "Running the saved scenario and checking results…"
                : "The agent is preparing your journey proposal…"}
            </p>
            <button onClick={cancel}>Cancel run</button>
          </>
        )}
        {draft.job?.status === "failed" && (
          <p role="alert">{draft.job.error}</p>
        )}
        {draft.job?.status === "cancelled" && (
          <p role="status">Cancelled. No completed result was produced by that attempt. You can run again.</p>
        )}
        <details>
          <summary>For engineers · sources and pack identity</summary>
          <p>{journey.source_refs.join(" · ")}</p>
          <code>{journey.pack_digest}</code>
          {result?.pack_names && <p>Frozen packs: {result.pack_names.join(", ")}</p>}
          {draft.journey_origin && (
            <>
              <h3>Reviewed operator decisions</h3>
              <p>{draft.journey_origin.decisions}</p>
              <p>Reviewed by {draft.journey_origin.reviewer}. The prepared source journey remains separate.</p>
            </>
          )}
        </details>
      </section>
      {!!draft.journey_coverage?.length && (
        <section className="wb-card">
          <details>
            <summary>For engineers · coverage and checks not run here</summary>
            <p>These are source assertion sites, not journey counts or pass rates. Run results below are separate.</p>
            {draft.journey_coverage.map((group, i) => (
              <div key={i}>
                <strong>{group.status === "implemented" ? "Represented here" : group.status === "pending-migration" ? "Not yet migrated to the UI" : "Supplemental · not run here"} · {group.sites.length} assertion sites</strong>
                <p>{group.reason}</p>
                <small>{group.source} · lines {group.sites.join(", ")}</small>
              </div>
            ))}
          </details>
        </section>
      )}
      {draft.journey_result_stale && (
        <p role="status" className="wb-notice">
          These results belong to an earlier engine, pack or story revision. Run
          again before relying on them.
        </p>
      )}
      {result && (
        <section className="wb-card">
          <h2>
            {draft.journey_result_stale ? "Earlier result · rerun needed" : result.passed && !inspection?.checks.some(check => check.warnings.length) ? "All checks passed" : "Story needs attention"}
          </h2>
          <p>
            {counts("passed")} passed · {counts("failed")} failed ·{" "}
            {counts("unsupported")} unsupported · {counts("error")} errors
          </p>
          <p>
            Storage for this recorded run: {result.backend === "spanner" ? "Spanner" : result.backend === "isolated-memory" ? "isolated memory" : "not recorded"}.
          </p>
          <p>
            Unsupported checks are not passes. This is semantic sandbox
            evidence; it does not verify HTTP authentication or a deployed
            service.
          </p>
          {results.filter((r: any) => r.actual?.categories && r.actual?.questions).map((r: any) => (
            <div key={`benchmark-${r.check_id}`}>
              <h3>Question evaluation</h3>
              <p>F1 measures overlap with the reviewed expected answer: 1 is an exact match. The baseline searches text without following relationships.</p>
              <table>
                <caption>Mean F1 by question category</caption>
                <thead><tr><th scope="col">Category</th><th scope="col">Graph retrieval</th><th scope="col">Text baseline</th></tr></thead>
                <tbody>{Object.entries(r.actual.categories).map(([category, scores]: [string, any]) => (
                  <tr key={category}><th scope="row">{category}</th><td>{scores.retrieval.toFixed(3)}</td><td>{scores.baseline.toFixed(3)}</td></tr>
                ))}</tbody>
              </table>
              {r.actual.questions.map((q: any) => <details key={q.question}>
                <summary>{q.question} — F1 {q.f1.toFixed(3)}; baseline {q.baseline_f1.toFixed(3)}</summary>
                <p>Expected: {q.expected.join(", ")}</p>
                <p>Retrieved: {q.found.join(", ") || "No answers"}</p>
                <p>Text baseline: {q.baseline_found.join(", ") || "No answers"}</p>
              </details>)}
            </div>
          ))}
          {inspection?.checks.some(check => check.warnings.length) && <p role="alert">Some assertions may pass without testing the intended behavior. Review the flagged prerequisites before treating this run as proof.</p>}
          {!allowed && <details><summary>Allow agent explanations for this story</summary><label><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />I reviewed this story for sensitive data and allow its events, pinned rules, specification and results to be sent to the agent's external service.</label><button disabled={!consent || busy} onClick={allowExplanations}>Save permission for explanations</button></details>}
          <label>
            <input
              type="checkbox"
              checked={failuresOnly}
              onChange={(e) => setFailuresOnly(e.target.checked)}
            />{" "}
            Show only checks needing attention
          </label>
          {results
            .filter((r: any) => !failuresOnly || r.status !== "passed" || inspection?.checks.find(check => check.id === r.check_id)?.warnings.length)
            .map((r: any) => {
              const check = journey.checks.find(
                (c: any) => c.id === r.check_id,
              );
              const detail = inspection?.checks.find(item => item.id === r.check_id);
              const checkIndex = journey.checks.findIndex((item: any) => item.id === r.check_id);
              return (
                <details key={r.check_id}>
                  <summary>
                    {r.status.toUpperCase()} · {check?.kind === "disposition" && r.status === "failed" ? explainCheck(check, r).split(". This compares")[0] : check?.description}
                  </summary>
                  <p>{explainCheck(check, r)}</p>
                  {detail?.differences?.map(line => <p key={line}><strong>{line}</strong></p>)}
                  {detail && <><p><strong>Where to inspect: {detail.guidance.category}</strong></p><p>{detail.guidance.action}</p><p>{detail.guidance.boundary}</p><p>{detail.guidance.rerun}</p>{detail.warnings.map(warning => <p role="alert" key={warning}>{warning}</p>)}</>}
                  {r.status !== "passed" && <CheckExplanation key={`${draft.id}:${draft.revision}:${r.check_id}`} ask={(question, signal) => askCheck(checkIndex, question, signal)} disabledReason={busy ? "Wait for the current task." : !allowed ? "Review and save provider permission above before asking the agent." : !explaining ? "The explanation agent is not configured." : draft.journey_result_stale ? "Rerun this pinned story before asking about old results." : ""} />}
                  <button className="wb-secondary" onClick={() => setSuggestion(`Investigate: ${check?.description}. ${detail?.guidance.action || "Compare the reviewed expectation and observed evidence."} Keep existing expectations unchanged unless an operator supplies a source-backed correction.`)}>Plan a follow-up story</button>
                  {check?.after_step != null && (
                    <button onClick={() => { setStep(check.after_step); requestAnimationFrame(() => { const timeline = document.getElementById("story-timeline"); timeline?.focus(); timeline?.scrollIntoView({block: "start"}); }); }}>
                      Inspect event {check.after_step + 1}
                    </button>
                  )}
                  <details><summary>For engineers · expected and observed evidence</summary>
                  <p>{r.explanation}</p>
                  <h3>Expected</h3>
                  <pre>{JSON.stringify(r.expected, null, 2)}</pre>
                  <h3>Observed</h3>
                  <pre>{JSON.stringify(r.actual, null, 2)}</pre>
                  </details>
                </details>
              );
            })}
          <details>
            <summary>Execution limits</summary>
            <ul>
              {result.limits.map((s: string) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </details>
        </section>
      )}
      {inspection && <section className="wb-card" aria-label="Story coverage">
        <h2>What this story checks</h2><p>{inspection.boundary}</p>
        {inspection.pack_issue && <p role="alert">The pinned pack could not be verified. Coverage is incomplete; inspect the saved pack before relying on this run.</p>}
        <label htmlFor="story-coverage-filter">Show coverage</label><select id="story-coverage-filter" value={coverageFilter} onChange={e => setCoverageFilter(e.target.value)}><option value="gaps">Gaps and checks needing attention</option><option value="all">All coverage items</option></select>
        <label>Find coverage<input value={coverageSearch} onChange={e => {setCoverageSearch(e.target.value);setCoverageLimit(8);}} /></label>
        <p>{coverageRows.length} matching items. This is a coverage inventory, not a completeness score.</p>
        <ul>{coverageRows.slice(0, coverageLimit).map((row, i) => <li key={`${row.kind}-${row.label}-${i}`}>
          <strong>{row.label.replace(/_/g, " ")} — {coverageLabels[row.status]}</strong><small>{row.kind} · {row.occurrences} matching event deliveries</small>
          {row.checks.length > 0 ? <details><summary>Checks behind this status</summary>{row.checks.map(id => {
            const detail = inspection.checks.find(c => c.id === id);return <p key={id}>{detail?.label} · {detail?.outcome || "not run"}</p>;
          })}</details> : <p>An event appearing in the story does not verify this behavior.</p>}
          {row.status !== "passing" && <button className="wb-secondary" onClick={() => setSuggestion(`Test ${row.kind}: ${row.label}. Define expected outcomes from the domain specification; do not infer them from a failed result.`)}>Plan a follow-up story</button>}
        </li>)}</ul>
        {coverageRows.length > coverageLimit && <button className="wb-secondary" onClick={() => setCoverageLimit(n => n + 8)}>Show eight more coverage items</button>}
        <details><summary>Every defined check</summary>{inspection.checks.map(check => <p key={check.id}>{check.label} — {coverageLabels[check.status]}{check.outcome ? ` (${check.outcome})` : ""}{check.warnings.map(warning => <span key={warning}> · {warning}</span>)}</p>)}</details>
        <p>Follow-up planning appends to your brief. Nothing is generated, sent or approved until you review the existing story-authoring form.</p>
      </section>}
      <JourneyAuthor
        key={draft.id}
        draft={draft}
        busy={busy}
        model={model}
        act={act}
        suggestion={suggestion}
      />
      <section className="wb-card" id="story-timeline" tabIndex={-1}>
        <h2>{journey.events.length ? "Story timeline" : "Starting test graph"}</h2>
        {journey.events.length > 0 ? <>
        <label>
          Step
          <select
            value={step}
            onChange={(e) => setStep(Number(e.target.value))}
          >
            {journey.events.map((e: any, i: number) => (
              <option key={e.id} value={i}>
                {i + 1}. {e.title}
              </option>
            ))}
          </select>
        </label>
        <details>
          <summary>Input event</summary>
          <pre>{JSON.stringify(journey.events[step].request, null, 2)}</pre>
        </details>
        </> : <details>
          <summary>Saved graph and retrieval settings</summary>
          <pre>{JSON.stringify(journey.starting_state, null, 2)}</pre>
        </details>}
        <details>
          <summary>{journey.events.length ? "Expected checks at this step" : "Expected retrieval checks"}</summary>
          {journey.checks
            .filter((c: any) => journey.events.length ? c.after_step === step : c.after_step == null)
            .map((c: any) => (
              <p key={c.id}>{c.description}</p>
            ))}
        </details>
        {snapshot ? (
          <>
            {journey.events.length > 0 && <p>
              Observed handling: <strong>{snapshot.outcome}</strong>
            </p>}
            <PackGraph
              mode="observed"
              nodes={snapshot.nodes.filter((n: any) => n.type !== "Event")}
              edges={snapshot.edges.filter(
                (e: any) => e.type !== "DERIVED_FROM",
              )}
            />
            <details>
              <summary>All stored nodes and relationships</summary>
              <pre>
                {JSON.stringify(
                  { nodes: snapshot.nodes, edges: snapshot.edges },
                  null,
                  2,
                )}
              </pre>
            </details>
          </>
        ) : (
          <p>
            {graphFixture ? "Run the fixture to inspect its loaded graph and query results." : "Run the journey to see the graph actually stored after this event."}
          </p>
        )}
      </section>
    </>
  );
}
