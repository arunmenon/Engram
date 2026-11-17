import { useEffect, useRef, useState } from "react";
import type { ExplainResult } from "./ExplainProblem";

/** Read-only use of the shared explain API; no oracle or pack mutation controls. */
export function CheckExplanation({ask, disabledReason}: {
  ask: (question: string, signal: AbortSignal) => Promise<ExplainResult>;
  disabledReason: string;
}) {
  const [question, setQuestion] = useState("What should I inspect to understand this failed check?");
  const [answer, setAnswer] = useState<ExplainResult | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => {generation.current++; controller.current?.abort();}, []);
  return <section aria-label="Ask about this check">
    <p>The guidance above comes from the recorded check. The agent can explain it; it cannot change the story or its expected answers here.</p>
    <label>Question for the agent<textarea value={question} maxLength={1000} onChange={e => setQuestion(e.target.value)} /></label>
    {disabledReason && <p>{disabledReason}</p>}
    <button disabled={!!disabledReason || loading || !question.trim()} onClick={async () => {
      const turn = ++generation.current; controller.current = new AbortController();setLoading(true);setAnswer(null);setMessage("");
      try {const result = await ask(question, controller.current.signal);if (turn === generation.current) setAnswer(result);}
      catch {if (turn === generation.current) setMessage("The explanation could not finish. Your story and expectations are unchanged. Check that the result is current before trying again.");}
      finally {if (turn === generation.current) setLoading(false);}
    }}>Explain this check</button>
    {loading && <button onClick={() => {generation.current++;controller.current?.abort();setLoading(false);setMessage("Stopped waiting. The earlier question may still be processing; allow it to finish before retrying.");}}>Stop waiting</button>}
    <p role="status">{loading ? "The agent is reading this check's recorded evidence…" : message}</p>
    {answer && <div><h4>Agent explanation · not a verified diagnosis</h4>
      {answer.answer.claims.map((claim, i) => <div key={i}><p>{claim.text}</p><details><summary>Supporting evidence</summary>{claim.evidence.map(id => <pre key={id}>{answer.evidence.find(ref => ref.id === id)?.text}</pre>)}</details></div>)}
      {!!answer.answer.missing.length && <ul>{answer.answer.missing.map(text => <li key={text}>{text}</li>)}</ul>}
    </div>}
  </section>;
}
