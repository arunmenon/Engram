import { useEffect, useRef, useState } from "react";
import type { Draft } from "./types";
import { affectedRules, type PreparedRequest } from "./requestDraft";

export function RequestReview({ draft, metadata, answer, text, setText, stale, disabledReason, onReview, onSend, onClear }: {
  draft: Draft; metadata: PreparedRequest; answer: string; text: string;
  setText: (value: string) => void; stale: boolean; disabledReason: string;
  onReview: () => Promise<void>; onSend: () => void; onClear: () => void;
}) {
  const [message, setMessage] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const field = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    field.current?.focus();
    field.current?.setSelectionRange(0, 0);
  }, []);
  const rules = affectedRules(draft.proposal?.pack, metadata.subject, answer || text);
  return <section id="workbench-request-review" className="wb-explain" aria-label="Review your request" tabIndex={-1}>
    <h4>Your request to the agent</h4>
    <p><strong>About:</strong> {metadata.subject || "Recovered request — the original issue is unavailable."}</p>
    <div role="region" aria-label="Change scope preview">
      <h4>What this request may affect</h4>
      <p><strong>{answer || metadata.answer ? "Requested outcome — your words:" : "Saved request:"}</strong> {answer || metadata.answer || "The original answer is unavailable. Review the retained instruction below."}</p>
      {rules.length ? <>
        <p>Records mentioned in this issue or request: {rules.map(r => r.name).join(", ")}. These are candidates to review, not confirmed changes.</p>
        <details><summary>Current rules · technical details</summary><ul>{rules.map(rule => <li key={rule.name}><strong>{rule.name}</strong>: currently identified by {rule.identity || "a key not shown here"}.
          {rule.states && <> Current states: {rule.states}.</>}
          {!!rule.events.length && <> Updated by: {[...new Set(rule.events)].join(", ")}.</>}
        </li>)}</ul></details>
      </> : <p>No affected record could be identified from the declared names. The agent must identify the relevant rule before proposing a change.</p>}
      <p>The exact field, event rule or answer behavior to change is not verified yet. Sending asks the agent to propose those changes; you will review the diff and test the result before accepting it.</p>
    </div>
    {stale && <p role="alert" className="wb-warning">This request needs review: the draft or your answer changed, or the request was restored. Your words are retained, but this is not a fresh agent recommendation. Check the current rule and edit the request before confirming.</p>}
    <label>Request to send<textarea id="workbench-inline-request" ref={field} rows={8} value={text} onChange={e => setText(e.target.value)} /></label>
    {answer !== metadata.answer && <p>Your answer changed since preparation. The request below has not been rewritten automatically; update it to match.</p>}
    {disabledReason && <p>{disabledReason}</p>}
    {stale && <button type="button" disabled={!!disabledReason || reviewing} onClick={async () => {
      setReviewing(true); setMessage("");
      try { await onReview(); setMessage("Request reviewed against the current draft. Nothing was sent."); field.current?.focus({preventScroll:true}); }
      catch (e) { setMessage(e instanceof Error ? e.message : "Could not confirm the current draft. Your text is retained."); }
      finally { setReviewing(false); }
    }}>I reviewed this request against the current draft</button>}
    <button type="button" disabled={stale || !!disabledReason || reviewing || !text.trim()} onClick={onSend}>Send request to the agent</button>
    <button type="button" className="wb-text" onClick={onClear}>Clear prepared request</button>
    <p role="status" aria-live="polite">{message}</p>
  </section>;
}
