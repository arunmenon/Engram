import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type { Draft } from "./types";
import { relationshipChanges, lifecycleComparison, decisionEvidence } from "./decisionSummary";

export type ExplainScope = "problem" | "limitation" | "author_error" | "pack" | "node" | "edge" | "decision" | "failed_check";
type Scope = ExplainScope;
export interface DecisionOption {
  id: string; label: string; explanation: string; evidence: string[];
  kind: "identity" | "lifecycle"; node_type: string;
  edits: {path: (string | number)[]; value: unknown}[];
}
interface PlannedEffects {
  record_count: number;
  records: {id: string; samples: number[]; identity?: Record<string, unknown>; events?: string[]}[];
  relationships: string[][];
  provenance_relationships?: string[][];
  transitions: {sample: number; event: string; record: string; to: string; only_from: string[] | null}[];
}
export interface ExplainResult {
  draft_id: string;
  revision: number;
  proposal_digest: string;
  scope: Scope;
  index: number;
  option_previews?: {id: string; available: boolean; reason?: string; detail?: string; before?: PlannedEffects; after?: PlannedEffects}[];
  answer: {
    kind: "supported" | "unknown" | "engine_limit";
    claims: { text: string; evidence: string[] }[];
    missing: string[];
    instruction: string | null;
    instruction_evidence: string[];
    options?: DecisionOption[];
  };
  evidence: { id: string; kind: string; text: string; source_id?: string }[];
}

export interface ExplanationViewState {
  open: boolean; question: string; answer: ExplainResult | null; message: string;

}
export function ExplainProblem({ answerInDecisions = false, draft, scope, index, disabledReason, ask, propose, choose, clarify, onMaterial, memory, memoryKey, hasPreparedRequest, clarifyDirect, requestText, setRequestText, sendRequest, sendDisabledReason, ownsRequest, description, setDescription, answerId, requestPanel, onExistingRequest }: {
  answerInDecisions?: boolean;
  answerId: string;
  description: string;
  setDescription: (text: string) => void;
  requestPanel: ReactNode;
  onExistingRequest: () => void;
  ownsRequest: boolean;
  clarifyDirect: (description: string) => Promise<void>;
  requestText: string;
  setRequestText: (text: string) => void;
  sendRequest: () => void;
  sendDisabledReason: string;
  memory: Map<string, ExplanationViewState>;
  memoryKey: string;
  hasPreparedRequest: boolean;
  draft: Draft;
  scope: Scope;
  index: number;
  disabledReason: string;
  ask: (question: string, signal: AbortSignal) => Promise<ExplainResult>;
  propose: (result: ExplainResult) => Promise<void>;
  choose: (result: ExplainResult, option: DecisionOption) => Promise<void>;
  clarify: (result: ExplainResult, description: string) => Promise<void>;
  onMaterial: () => Promise<void>;
}) {
  const saved = memory.get(memoryKey);
  const reasonId = useId();
  const [withdrawn, setWithdrawn] = useState(() => !saved?.answer && scope === "decision" && [...memory.entries()].some(([key, value]) =>
    key !== memoryKey && value.answer?.draft_id === draft.id && value.answer.scope === scope && value.answer.index === index && !!value.answer.answer.options?.length));
  const [open, setOpen] = useState(saved?.open ?? false);
  const [question, setQuestion] = useState(saved?.question ?? "What does this mean, and what are my options?");
  const [answer, setAnswer] = useState<ExplainResult | null>(saved?.answer ?? null);
  const [message, setMessage] = useState(saved?.message ?? "");
  const [loading, setLoading] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [errorDetail, setErrorDetail] = useState("");
  const [askedQuestion, setAskedQuestion] = useState("");
  const controller = useRef<AbortController | null>(null);
  const serial = useRef(0);
  const resultRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    memory.set(memoryKey, {open, question, answer, message});
    if (memory.size > 20) memory.delete(memory.keys().next().value!);
  }, [memory, memoryKey, open, question, answer, message]);
  useEffect(() => () => { serial.current++; controller.current?.abort(); }, []);
  async function run() {
    const generation = ++serial.current;
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    setLoading(true); setAnswer(null); setMessage(""); setErrorDetail(""); setAskedQuestion(question);
    try {
      const result = await ask(question, nextController.signal);
      if (generation !== serial.current) return;
      setAnswer(result); setWithdrawn(false);
      setMessage("Explanation ready. Nothing in this pack has changed.");
      requestAnimationFrame(() => resultRef.current?.focus());
    } catch (error) {
      if (generation === serial.current) { setMessage("The agent could not answer. Your inputs are kept. Try again or leave this unresolved."); setErrorDetail(error instanceof Error ? error.message : "Request failed"); }
    } finally {
      if (generation === serial.current) setLoading(false);
    }
  }
  return <section className="wb-explain" aria-label={`Explain ${scope} ${index + 1}`}>
    <button type="button" className="wb-secondary" aria-expanded={open} aria-describedby={disabledReason || withdrawn ? reasonId : undefined} disabled={!!disabledReason || loading} onClick={() => { setOpen(true); void run(); }}>Explain this</button>
    {(disabledReason || withdrawn) && <p id={reasonId} role="status">{withdrawn && "Options withdrawn because the draft changed. "}{disabledReason || "Ask again to compare choices against the current draft."}</p>}
    {open && <div>
      {draft.proposal_stale && draft.explain_stale_allowed && <p>This explains the retained proposal. Your new request has not been applied yet.</p>}
      <p>Ask about this item. This reads the saved draft; it does not change or accept the pack.</p>
      <details><summary>Ask a different question</summary><label>Your question<textarea value={question} maxLength={1000} onChange={e => setQuestion(e.target.value)} /></label>
      {disabledReason && <p>{disabledReason}</p>}
      <button type="button" disabled={!!disabledReason || loading || !question.trim()} onClick={() => void run()}>Ask for an explanation</button></details>
      {loading && <button type="button" className="wb-secondary" onClick={() => {
        serial.current++; controller.current?.abort(); setLoading(false);
        setMessage("Stopped waiting for this explanation. Your pack is unchanged; the provider may still finish its request.");
      }}>Stop waiting</button>}
      <p role="status" aria-live="polite">{loading ? "The agent is explaining this item…" : message}</p>
      {askedQuestion && <p><strong>You asked:</strong> {askedQuestion}</p>}
      {errorDetail && <details><summary>Error details for support</summary><p>{errorDetail}</p></details>}
      {answer && <div ref={resultRef} tabIndex={-1}>
        <h4>{answer.answer.kind === "unknown" ? "Help the agent understand this" : "What this means"}</h4>
        {answer.answer.claims.map((claim, i) => <div key={i}><p>{claim.text}</p>
          <details><summary>Why the agent says this</summary>{claim.evidence.map(id => {
            const ref = answer.evidence.find(e => e.id === id);
            return <blockquote key={id}><small>{ref?.kind === "limitation" ? "Agent-reported limitation; not an independent engine check" : ref?.kind === "source" ? `Source: ${ref.source_id}` : ref?.kind === "engine_capability" ? "Supported engine settings" : ["pack", "node", "edge"].includes(ref?.kind || "") ? "Current pack settings" : ref?.kind === "decision" ? "Recorded decision" : ref?.kind === "operator_decision" ? "Recorded operator question or answer" : ref?.kind === "author_error" ? "Recorded authoring failure" : "Recorded engine check"}</small><p>{ref?.kind === "decision" ? decisionEvidence(ref.text) : ref?.text}</p></blockquote>;
          })}</details></div>)}
        {!!answer.answer.missing.length && <ul>{answer.answer.missing.map((text, i) => <li key={i}>{text}</li>)}</ul>}
        {!!answer.answer.options?.length && <section aria-label="Compare choices">
          <h4>Compare choices using your examples</h4>
          <p>These are planned effects, not executed results. Neither choice is selected for you. Preparing a choice changes nothing in the pack.</p>
          {answer.evidence.some(ref => ref.kind === "source") && <details><summary>Supplied material for this decision</summary>
            <p>These excerpts may disagree. Review the relevant policy before choosing; the preview does not settle conflicting policies.</p>
            {answer.evidence.filter(ref => ref.kind === "source").map(ref => <blockquote key={ref.id}><small>Source: {ref.source_id}</small><p>{ref.text}</p></blockquote>)}
          </details>}
          {answer.answer.options.map(option => {
            const preview = answer.option_previews?.find(item => item.id === option.id);
            return <article key={option.id} className="wb-card">
              <h4>{option.label}</h4><p>{option.explanation}</p>
              {preview?.available && preview.before && preview.after ? <>
                {option.kind === "identity" ? <>
                  <p>With these examples: {preview.before.record_count} distinct records under the current rules → {preview.after.record_count} with this choice.</p>
                  <ul>{preview.after.records.map((record, i) => <li key={record.id}><strong>{record.identity && Object.keys(record.identity).length ? Object.entries(record.identity).map(([field, value]) => `${field.replace(/_/g, " ")}: ${String(value)}`).join(" · ") : record.id}</strong> — sample events {record.samples.join(", ")}{!!record.events?.length && <small>{record.events.map(event => event.replace(/_/g, " ").replace(/\./g, " ")).join(", ")}</small>}</li>)}</ul>
                  <p>This compares how the rules group your examples. It does not prove that records outside these examples will stay separate.</p>
                </> : <>
                  <p>This compares the current and proposed rules. It does not execute state changes or confirm which requests would be accepted.</p>
                  <ul>{lifecycleComparison(preview.before.transitions, preview.after.transitions, draft.proposal?.pack?.types?.nodes?.[option.node_type]?.lifecycle?.initial).map(({current, next, unrepresented}, i) => <li key={i}>
                    Sample {next.sample}: current rule requests “{current?.to || "unknown"}”, allowed from {current ? current.only_from?.length ? current.only_from.join(", ") : "any prior state" : "unknown"}; proposed rule requests “{next.to}”, allowed from {next.only_from?.length ? next.only_from.join(", ") : "any prior state"}.
                    {!!unrepresented.length && <p>This sample does not exercise the difference for starting state {unrepresented.map(state => `“${state}”`).join(", ")}: no earlier sample requests that state for this record. Add a sequence with a record already in that state to test the difference.</p>}
                  </li>)}</ul>
                  <p>Matching requests are not proof of matching results. Use a sandbox run to check the full sequence and starting states.</p>
                </>}
                {preview.before.relationships.length || preview.after.relationships.length ? <div><p>Business relationships in these examples:</p><ul>{relationshipChanges(preview.before.relationships, preview.after.relationships).map(change => <li key={change.name}>{change.name}: {change.before} → {change.after}{change.added || change.removed ? ` (${change.added} links added, ${change.removed} removed)` : " (unchanged)"}</li>)}</ul></div> : <p>No business relationship change in these examples.</p>}
                <details><summary>Inspect current and proposed rules</summary>
                  <p>Provenance links to source events (separate from business relationships): {preview.before.provenance_relationships?.length ?? "not reported"} before, {preview.after.provenance_relationships?.length ?? "not reported"} with this choice.</p>
                  <pre>{JSON.stringify({before: preview.before, proposed: preview.after, edits: option.edits}, null, 2)}</pre>
                </details>
              </> : <><p id={`${reasonId}-${option.id}`}>{preview?.reason || "This choice has no verified sample preview. Leave it unresolved or add representative events."}</p>
                {preview?.detail && <details><summary>Preview check details</summary><p>{preview.detail}</p></details>}</>}
              <details><summary>Sources for this choice</summary>{option.evidence.map(id => <blockquote key={id}>{(() => { const ref = answer.evidence.find(item => item.id === id); return ref?.kind === "decision" ? decisionEvidence(ref.text) : ref?.text; })()}</blockquote>)}</details>
              <button type="button" aria-describedby={disabledReason ? reasonId : !preview?.available ? `${reasonId}-${option.id}` : undefined} disabled={!!disabledReason || preparing || !preview?.available} onClick={async () => {
                if (hasPreparedRequest) { onExistingRequest(); setMessage("Your existing request is kept. This choice was not added. Review or clear that request first."); return; }
                setPreparing(true);
                try { await choose(answer, option); setMessage("Choice prepared for review. The pack and expected answers are unchanged."); }
                catch (error) { setMessage(error instanceof Error ? error.message : "Draft changed. Ask again."); }
                finally { setPreparing(false); }
              }}>Prepare this choice</button>
            </article>;
          })}
        </section>}
        {answer.answer.instruction && <div>
          <h4>Suggested next step</h4>
          <p>Prepare a correction for your review. You decide whether to send it.</p>
          <details><summary>Inspect the exact revision request</summary><p>{answer.answer.instruction}</p></details>
          <p>You can edit this request before sending it to the agent. No change has been applied.</p>
          <button type="button" disabled={!!disabledReason || preparing} onClick={async () => {
            setPreparing(true);
            try { await propose(answer); setMessage("Request prepared here. Review it before sending."); }
            catch (error) { setMessage(error instanceof Error ? error.message : "Draft changed. Ask again."); }
            finally { setPreparing(false); }
          }}>Propose this change</button>
        </div>}
      </div>}
    </div>}
    {!answerInDecisions && (scope === "limitation" || (["pack", "node", "edge"].includes(scope) && open) || answer?.answer.kind === "unknown") && <div>
      <label>Your answer<textarea id={answerId} maxLength={2500} rows={3} value={description}
        onChange={e => setDescription(e.target.value)} placeholder="Describe the rule your team follows. You can also say what you are unsure about." /></label>
      <p>You can answer now or add a document. Your answer is an instruction for the agent to consider; it does not change the pack.</p>
      {disabledReason && !open && <p>{disabledReason}</p>}
      <button type="button" disabled={!!disabledReason || preparing || !description.trim()} onClick={async () => {
        setPreparing(true);
        try {
          if (answer?.answer.kind === "unknown") await clarify(answer, description); else await clarifyDirect(description);
          setMessage("Request prepared here. Review it before sending.");
        } catch (error) { setMessage(error instanceof Error ? error.message : "Could not prepare the request. Your answer is retained."); }
        finally { setPreparing(false); }
      }}>Review my request</button>
      <button type="button" className="wb-secondary" disabled={preparing} onClick={() => void onMaterial().catch(error => setMessage(String(error)))}>Add supporting material</button>
      <button type="button" className="wb-text" onClick={() => setMessage("Left unresolved. Nothing was sent or approved." + (hasPreparedRequest ? " Your prepared request is retained. Review or clear it before sending later." : " Your answer stays here while you browse this draft."))}>Leave unresolved</button>
    </div>}
    {answerInDecisions && description && <p>Earlier note retained: {description}</p>}
    {!open && <p role="status" aria-live="polite">{message}</p>}
    {hasPreparedRequest && !ownsRequest && <button type="button" className="wb-secondary" onClick={onExistingRequest}>Review or clear the existing request</button>}
    {requestPanel}
  </section>;
}
