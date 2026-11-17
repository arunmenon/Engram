import { IntakeEvidence } from "./IntakeEvidence";
import { suggestCategory, sourceLabels } from "./intake";
import { reviewTicksFor, type ReviewTicks } from "./reviewTicks";
import { RequestReview } from "./RequestReview";
import { answerKey, requestNeedsReview, type PreparedRequest } from "./requestDraft";
import { ExplainProblem, type ExplainScope, type ExplainResult, type ExplanationViewState } from "./ExplainProblem";
import { sandboxGuidance } from "./results";
import { preserveEdits, changedFields, recoveryKey, readRecovery, resumeKey, readResumeStep, type Recovery } from "./editing";
import { JourneyWorkspace } from "./JourneyWorkspace";
import { AuthorSession, ModelReview, journey, nextTask } from "./OperatorFlow";
import { EntityPicker, sampleEntities } from "./EntityPicker";
import { PackGraph } from "./PackGraph";
import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  FileText,
  Layers3,
  Plus,
  ShieldCheck,
} from "lucide-react";
import type { Capabilities, Content, Draft, Source } from "./types";
import { initialContent } from "./types";
import "./workbench.css";

const steps = [
  "Tenant setup",
  "What describes their world?",
  "How Engram understands them",
  "Under the hood",
  "Questions to answer",
  "Test with examples",
  "Approve and hand off",
];
const split = (value: string) =>
  value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
const pretty = (value: unknown) => JSON.stringify(value, null, 2);

export default function Workbench() {
  const [retrievalScenario, setRetrievalScenario] = useState("retrieval-trust");
  const [token, setToken] = useState("");
  const [credential, setCredential] = useState("");
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [capacity, setCapacity] = useState<{ available: number; capacity: number; slots: { resource: string; state: string }[] } | null>(null);
  const [capacityError, setCapacityError] = useState(false);
  const [tenants, setTenants] = useState<Draft[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [content, setContent] = useState<Content | null>(null);
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [authorFailureDetail, setAuthorFailureDetail] = useState("");
  const [notice, setNotice] = useState("");
  const [connectionNotice, setConnectionNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [environment, setEnvironment] = useState("development");
  const [sourceKind, setSourceKind] = useState<Source["kind"]>("specification");
  const [sourceName, setSourceName] = useState("");
  const [sourceText, setSourceText] = useState("");
  const [selectedEvent, setSelectedEvent] = useState(0);
  const [authorPrompt, setAuthorPrompt] = useState("");
  const [reviewTicks, setReviewTicks] = useState<ReviewTicks | null>(null);
  const submittedAuthor = useRef<{id: string; prompt: string; afterRevision: number} | null>(null);
  const [preparedRequest, setPreparedRequest] = useState<PreparedRequest | null>(null);
  const [operatorAnswers, setOperatorAnswers] = useState<Record<string, string>>({});
  const [exported, setExported] = useState<any>(null);
  const [conflict, setConflict] = useState<Draft | null>(null);
  const [recovery, setRecovery] = useState<Recovery | null>(null);
  const [recoveryError, setRecoveryError] = useState("");
  const latest = useRef({ draft, content });
  latest.current = { draft, content };
  const requestBusy = useRef(false);
  const selection = useRef(0);
  const dirty =
    !!draft && !!content && pretty(content) !== pretty(draft.content);
  const running = draft?.job?.status === "running";
  const explanationMemory = useRef(new Map<string, ExplanationViewState>());
  const [materialReturn, setMaterialReturn] = useState<{id: string; revision: number} | null>(null);
  const explainTarget = useRef({id: draft?.id, revision: draft?.revision, prompt: authorPrompt, dirty});
  explainTarget.current = {id: draft?.id, revision: draft?.revision, prompt: authorPrompt, dirty};

  async function request(
    path: string,
    method = "GET",
    body?: unknown,
    key = token,
    signal?: AbortSignal,
  ) {
    const response = await fetch(`/admin${path}`, {
      signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(35000)]) : AbortSignal.timeout(30000),
      method,
      headers: {
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
    const result = await response.json().catch(() => {
      throw new Error("Engram could not return a usable response. Your typed input is retained; retry when the service is available.");
    });
    if (!response.ok)
      throw new Error(
        typeof result.detail === "string"
          ? result.detail
          : pretty(result.detail),
      );
    return result;
  }
  useEffect(() => {
    setCapacity(null);
    setCapacityError(false);
    if (!token || caps?.sandbox !== "spanner") return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const status = await request("/sandbox-capacity");
        if (!stopped) { setCapacity(status); setCapacityError(false); }
      } catch {
        if (!stopped) { setCapacity(null); setCapacityError(true); }
      } finally {
        if (!stopped) timer = setTimeout(refresh, 10000);
      }
    }
    void refresh();
    return () => { stopped = true; clearTimeout(timer); };
  }, [token, caps?.sandbox]);

  async function perform(action: () => Promise<void>) {
    if (requestBusy.current) return;
    requestBusy.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      requestBusy.current = false;
      setBusy(false);
    }
  }
  function receive(next: Draft, submitted?: Content, force = false) {
    const prior = latest.current;
    if (prior.draft?.id === next.id && next.revision < prior.draft.revision) return;
    if (!force && prior.draft?.id === next.id && prior.content) {
      if (!submitted && changedFields(prior.draft.content, next.content).length &&
          changedFields(prior.draft.content, prior.content).length) {
        setConflict(next);
        return;
      }
      const merged = preserveEdits(submitted || prior.draft.content, prior.content, next.content);
      latest.current = { draft: next, content: merged };
      setContent(merged);
    } else {
      latest.current = { draft: next, content: next.content };
      setContent(next.content);
    }
    setDraft(next);
    setExported(null);
  }
  async function open(id: string) {
    const serial = ++selection.current;
    setDraft(null);
    setContent(null);
    latest.current = { draft: null, content: null };
    setConflict(null);
    setRecovery(null);
    setExported(null);
    setSourceName("");
    setSourceText("");
    setAuthorPrompt("");
    setPreparedRequest(null); setOperatorAnswers({}); setReviewTicks(null);
    setSelectedEvent(0);
    setStep(0);
    setError(""); setAuthorFailureDetail("");
    const next = await request(`/tenants/${id}`);
    if (serial === selection.current) {
      receive(next, undefined, true);
      try {
        setStep(readResumeStep(localStorage.getItem(resumeKey(caps!.operator, id))));
        const key = recoveryKey(caps!.operator, id);
        const saved = readRecovery(sessionStorage.getItem(key));
        if (!saved) sessionStorage.removeItem(key);
        if (saved) {
          setReviewTicks(reviewTicksFor(next, saved.reviewTicks || null));
          setStep(saved.step);
          if (pretty(saved.content) !== pretty(next.content) || saved.sourceText || saved.sourceName || saved.authorPrompt || Object.values(saved.operatorAnswers || {}).some(Boolean)) setRecovery(saved);
        }
      } catch { setRecoveryError("Browser recovery is unavailable; keep this tab open until you save."); }
    }
  }
  function patch(change: Partial<Content>) {
    setContent((c) => c && { ...c, ...change });
    setNotice("");
  }
  async function save(value = content): Promise<Draft> {
    if (conflict || recovery) throw new Error("Resolve the saved-versus-typed changes before continuing.");
    if (!draft || !content) throw new Error("Select a tenant draft first");
    if (!value) throw new Error("Select a tenant first");
    if (pretty(value) === pretty(draft.content)) return draft;
    const localAtSubmit = latest.current.content || content;
    const next = await request(`/tenants/${draft.id}`, "PUT", {
      revision: draft.revision,
      content: value,
    });
    receive(next, localAtSubmit);
    setNotice(
      value.graph_reviewed && !next.content.graph_reviewed
        ? "Your graph selections were saved, but their review confirmation was cleared because the selections changed. Return to Questions to answer, review the saved selections and confirm them again."
        : "Saved. Test results must be rerun after changes; source and pack changes also need pack review.",
    );
    return next;
  }
  async function action(endpoint: string, extra = {}) {
    const current = await save();
    receive(
      await request(`/tenants/${current.id}/${endpoint}`, "POST", {
        revision: current.revision,
        ...(endpoint === "review"
          ? { rejected_facts: current.review?.rejected_facts || [] }
          : {}),
        ...extra,
      }),
    );
  }
  async function authorModel() {
    if (!content) return;
    if (preparedRequest && requestNeedsReview(preparedRequest, draft!, operatorAnswers[preparedRequest.itemKey] ?? preparedRequest.answer)) {
      setError("Review the prepared request against the current draft before sending."); focusRequest(); return;
    }
    const submittedPrompt = authorPrompt;
    setAuthorFailureDetail("");
    await perform(async () => {
      const current = await save({ ...content, instruction: submittedPrompt });
      try {
        submittedAuthor.current = {id: current.id, prompt: submittedPrompt, afterRevision: current.revision};
        receive(await request(`/tenants/${current.id}/author`, "POST", {revision: current.revision}));
      } catch (failure) {
        submittedAuthor.current = null;
        setAuthorFailureDetail(failure instanceof Error ? failure.message : "Request failed");
        throw new Error("The agent could not start. Your answer and request are kept. Review the saved draft, then retry when ready.");
      }
      // Keep the request until completion; accepting a job is not a successful revision.
    });
  }
  useEffect(() => {
    const submitted = submittedAuthor.current;
    if (!submitted || draft?.id !== submitted.id || draft.revision <= submitted.afterRevision || draft.job?.kind !== "author") return;
    if (!["completed", "failed", "cancelled"].includes(draft.job.status)) return;
    submittedAuthor.current = null;
    if (draft.job.status === "completed" && explainTarget.current.prompt === submitted.prompt) {
      setAuthorPrompt(""); setPreparedRequest(null);
    }
    // Failed/cancelled requests retain their text and become stale via the revision fence.
  }, [draft?.id, draft?.revision, draft?.job?.status]);

  async function go(index: number) {
    await perform(async () => {
      await save();
      setStep(index);
      setSelectedEvent(0);
    });
  }
  useEffect(() => {
    if (!draft) return;
    const id = draft.id, serial = selection.current;
    let stopped = false;
    let timer: number;
    const poll = async () => {
      try {
        const next = await request(`/tenants/${id}`);
        if (!stopped && serial === selection.current && !requestBusy.current) {
          receive(next); setConnectionNotice("");
        }
      } catch (e) {
        if (!stopped && serial === selection.current) setConnectionNotice("Connection interrupted. Your input is retained; checking for the service to return…");
      }
      if (!stopped) timer = window.setTimeout(poll, 1500);
    };
    timer = window.setTimeout(poll, 1500);
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [draft?.id, token]);

  useEffect(() => {
    if (!draft || !content || !caps || recovery || conflict) return;
    try {
      localStorage.setItem(resumeKey(caps.operator, draft.id), String(step));
      sessionStorage.setItem(recoveryKey(caps.operator, draft.id), JSON.stringify({
        savedAt: Date.now(), revision: draft.revision, content, step,
        sourceName, sourceText, sourceKind, authorPrompt, operatorAnswers, preparedRequest, reviewTicks,
      } satisfies Recovery));
    } catch { setRecoveryError("Browser recovery is unavailable. Save before closing this tab."); }
  }, [draft?.id, draft?.revision, content, step, sourceName, sourceText, sourceKind, authorPrompt, operatorAnswers, preparedRequest, reviewTicks, recovery, conflict]);

  useEffect(() => {
    if (recovery) requestAnimationFrame(() => document.getElementById("workbench-recovery")?.focus());
  }, [recovery]);
  async function addSource() {
    if (!sourceName.trim() || !sourceText.trim()) {
      setError("Name the source and add its contents.");
      return;
    }
    if (sourceText.length > 40000) {
      setError("Each input is limited to 40,000 characters.");
      return;
    }
    if (sourceKind !== "specification") {
      try {
        JSON.parse(sourceText);
      } catch {
        setError("Schemas and sample events must be valid JSON.");
        return;
      }
    }
    if (!content) return;
    const addedName = sourceName, addedText = sourceText;
    await save({
      ...content,
      sources: [
        ...content.sources,
        {
          id: crypto.randomUUID(),
          kind: sourceKind,
          name: sourceName.trim(),
          text: sourceText,
        },
      ],
    });
    setSourceName(value => value === addedName ? "" : value);
    setSourceText(value => value === addedText ? "" : value);
    setError("");
    setNotice(
      "Source added and saved. Review its category in the evidence list below.",
    );
  }

  if (!caps)
    return (
      <div className="wb">
        <main className="wb-login">
          <div className="wb-brand">
            <Layers3 /> ENGRAM <span>OPERATOR WORKSPACE</span>
          </div>
          <h1>
            Build a tenant’s pack.
            <br />
            Test it before handoff.
          </h1>
          <p>
            Tenant-specific pack authoring, from supplied material to a
            reviewed pack.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void perform(async () => {
                const next = await request(
                  "/capabilities",
                  "GET",
                  undefined,
                  credential,
                );
                setToken(credential);
                setCredential("");
                setCaps(next);
                setTenants(
                  await request("/tenants", "GET", undefined, credential),
                );
              });
            }}
          >
            <label>
              Operator access token
              <input
                type="password"
                autoComplete="off"
                required
                value={credential}
                onChange={(e) => setCredential(e.target.value)}
              />
            </label>
            <button disabled={busy}>
              Open workspace <ArrowRight size={16} />
            </button>
          </form>
          <p className="wb-muted">
            Credentials stay in memory for this session. This workspace cannot
            activate live tenants.
          </p>
          {error && (
            <p role="alert" className="wb-error">
              {error}
            </p>
          )}
        </main>
      </div>
    );

  const pack = draft?.proposal?.pack;
  const entities = sampleEntities(draft);
  const entityLabel = (id: string) =>
    entities.find((e) => e.id === id)?.label || id;
  const facts = draft?.proposal?.facts || [];
  const reviewed = draft?.review?.accepted_facts || [];
  const rejected = draft?.review?.rejected_facts || [];
  const producers = [
    ...new Set([
      ...(content?.producer_ids || []),
      ...(content?.sources || [])
        .filter((s) => s.kind === "samples")
        .flatMap((s) => {
          try {
            const raw = JSON.parse(s.text);
            return (Array.isArray(raw) ? raw : [raw])
              .map((e: any) => e.producer_id)
              .filter((v: any) => typeof v === "string");
          } catch {
            return [];
          }
        }),
    ]),
  ] as string[];
  const context = content && draft;
  const next = context ? (authorPrompt.trim() && preparedRequest && (content.data_policy !== "provider_allowed" || !content.redaction_confirmed) ? {
    step: 0, title: "Review data handling before sending", reason: "The current permission settings prevent sending this request. Keep it local, or review permission and redaction in Tenant setup.",
  } : authorPrompt.trim() && preparedRequest && draft.job?.kind === "author" && draft.job.status === "failed" ? {
    step: 2, title: "The agent could not finish this request", reason: `${draft.job.error || "The revision failed."} Your answer and request are kept. Review the retained request to retry, or clear it.`,
  } : authorPrompt.trim() && preparedRequest ? {
    step: 2, title: "Review your prepared request", reason: preparedRequest.subject || "Your recovered request is ready to inspect. Nothing has been sent.",
  } : nextTask(draft, content)) : null;
  const focusRequest = () => requestAnimationFrame(() => {
    const field = document.getElementById("workbench-inline-request") as HTMLTextAreaElement | null;
    (field || document.getElementById("workbench-request-review"))?.focus();
    if (field) { field.setSelectionRange(0, 0); field.scrollTop = 0; }
  });
  const requestReason = dirty ? "Save your input changes before reviewing or sending." :
    content?.data_policy !== "provider_allowed" || !content?.redaction_confirmed ? "Allow provider use and confirm redaction in Tenant setup first." :
    busy || running ? "Wait for the current task to finish." : !caps?.authoring ? "The authoring agent is not configured." :
    !content?.scope.trim() || !content?.sources.length ? "Add the tenant scope and at least one source before sending." : "";
  function renderRequestReview() {
    if (!draft || !preparedRequest || !authorPrompt.trim()) return null;
    const humanAnswer = operatorAnswers[preparedRequest.itemKey] ?? preparedRequest.answer;
    return <RequestReview draft={draft} metadata={preparedRequest} answer={humanAnswer}
      text={authorPrompt} setText={setAuthorPrompt}
      stale={requestNeedsReview(preparedRequest, draft, humanAnswer)} disabledReason={requestReason}
      onReview={async () => {
        const current = await request(`/tenants/${draft.id}`) as Draft;
        if (explainTarget.current.id !== current.id || explainTarget.current.dirty || current.revision !== draft.revision)
          throw new Error("The draft changed again. Review the latest saved version first.");
        setPreparedRequest({...preparedRequest, reviewedRevision: current.revision, proposal: JSON.stringify(current.proposal), answer: humanAnswer});
      }}
      onSend={() => void authorModel()} onClear={() => {
        setAuthorPrompt(""); setPreparedRequest(null);
        requestAnimationFrame(() => (document.getElementById(`answer-${encodeURIComponent(preparedRequest.itemKey)}`) || document.getElementById("workbench-pack-question-target"))?.focus());
      }} />;
  }
  function subjectFor(scope: ExplainScope, index: number): string {
    const pack = draft?.proposal?.pack;
    if (scope === "decision") return draft?.proposal?.decisions[index]?.question || "";
    if (scope === "pack") return `Pack: ${pack?.pack?.name || "current proposal"}`;
    if (scope === "node" || scope === "edge") {
      const section = pack?.types?.[scope === "node" ? "nodes" : "edges"] || {};
      const name = Object.keys(section).sort()[index];
      return name ? `${name}: ${JSON.stringify(section[name])}` : "";
    }
    return scope === "limitation" ? draft?.proposal?.limitations[index] || "" :
      scope === "problem" ? draft?.validation?.problems[index] || "" : draft?.job?.error || "";
  }
  const visibleRequestOwner = draft && preparedRequest && (["limitation", "problem", "author_error"] as ExplainScope[]).some(scope => {
    const count = scope === "limitation" ? draft.proposal?.limitations.length || 0 : scope === "problem" ? draft.validation?.problems.length || 0 : draft.job?.kind === "author" && draft.job.status === "failed" ? 1 : 0;
    return Array.from({length: count}, (_, index) => answerKey(draft.id, scope, subjectFor(scope, index))).includes(preparedRequest.itemKey);
  });
  async function prepareExplanationRequest(result: Pick<ExplainResult, "draft_id" | "revision">, text: string) {
    const current = await request(`/tenants/${result.draft_id}`) as Draft;
    if (explainTarget.current.id !== result.draft_id || explainTarget.current.revision !== result.revision || explainTarget.current.dirty || current.revision !== result.revision)
      throw new Error("The draft changed. Ask again before preparing a revision.");
    if (explainTarget.current.prompt.trim()) throw new Error("Your revision request already has text. Keep or clear it before preparing another request.");
    setAuthorPrompt(text);

  }
  function renderExplanation(scope: ExplainScope, index: number) {
    if (!draft || !content || !caps) return null;
    const subject = subjectFor(scope, index);
    const itemKey = answerKey(draft.id, scope, subject);
    const prepareForItem = async (result: Pick<ExplainResult, "draft_id" | "revision">, text: string) => {
      await prepareExplanationRequest(result, text);
      setPreparedRequest({itemKey, subject, answer: operatorAnswers[itemKey] || "", reviewedRevision: result.revision, proposal: JSON.stringify(draft.proposal)});
      focusRequest();
    };
    const memoryKey = `${draft.id}:${draft.revision}:${scope}:${index}:${JSON.stringify(draft.proposal)}`;
    return <ExplainProblem key={memoryKey} memoryKey={memoryKey} memory={explanationMemory.current} hasPreparedRequest={!!authorPrompt.trim()}
      answerInDecisions={(scope === "limitation" || scope === "decision") && !!draft.proposal?.decisions.length}
      draft={draft} scope={scope} index={index}
      answerId={`answer-${encodeURIComponent(itemKey)}`} description={operatorAnswers[itemKey] || ""} setDescription={text => setOperatorAnswers(values => ({...values, [itemKey]:text}))}
      requestPanel={!["pack", "node", "edge", "decision"].includes(scope) && preparedRequest?.itemKey === itemKey ? renderRequestReview() : null} onExistingRequest={focusRequest}
      ownsRequest={preparedRequest?.itemKey === itemKey} requestText={authorPrompt} setRequestText={setAuthorPrompt} sendRequest={() => void authorModel()}
      sendDisabledReason={dirty ? "Save your input changes before sending." : content.data_policy !== "provider_allowed" || !content.redaction_confirmed ? "Allow provider use and confirm redaction in Tenant setup first." : busy || running ? "Wait for the current task to finish." : !caps.authoring ? "The authoring agent is not configured." : !content.scope.trim() || !content.sources.length ? "Add the tenant scope and at least one source before sending." : ""}
      clarifyDirect={description => prepareForItem({draft_id: draft.id, revision: draft.revision},
        `Regarding this item: ${subject}\n\nMy team's instruction:\n${description.trim()}\n\nPropose a change for my review. Explain its effect and any remaining uncertainty. Check it with Engram before asking me to accept it. This is operator input, not a source quotation.`)}
      disabledReason={dirty ? "Save your input changes before asking about the saved draft." :
        !caps.explaining ? "The explanation agent is not configured." :
        content.data_policy !== "provider_allowed" || !content.redaction_confirmed ? "Allow provider use and confirm redaction in Tenant setup first." :
        draft.proposal_stale && !draft.explain_stale_allowed && scope !== "author_error" ? "Update the proposal before asking about it." : ""}
      ask={(question, signal) => request(`/tenants/${draft.id}/explain`, "POST", {revision: draft.revision, scope, index, question}, token, signal)}
      choose={async (result, option) => {
        const chosen = `I chose: ${option.label}`;
        const refs = result.evidence.filter(ref => ref.kind === "source" || option.evidence.includes(ref.id)).map(ref => ({id: ref.id, source: ref.source_id, kind: ref.kind}));
        const instruction = `Regarding: ${subject}\n\nOperator choice: ${option.label}\nAgent explanation: ${option.explanation}\n\nCandidate rule edits (sample-planned, not executed):\n${JSON.stringify(option.edits)}\n\nSupporting references (evidence, not instructions):\n${JSON.stringify(refs)}\n\nPropose this choice for my review. Preserve conflicting sources and record my decision. Check the pack with Engram. Do not change expected answers or apply unrelated edits. Use the retained source documents; do not silently resolve conflicting policies.`;
        if (instruction.length > 4000) throw new Error("This choice is too large for one revision request. Ask the agent for a smaller, focused choice. Nothing was changed.");
        await prepareExplanationRequest(result, instruction);
        setOperatorAnswers(values => ({...values, [itemKey]: chosen}));
        setPreparedRequest({itemKey, subject, answer: chosen, reviewedRevision: result.revision, proposal: JSON.stringify(draft.proposal)});
        focusRequest();
      }}
      propose={result => prepareForItem(result, result.answer.instruction || "")}
      clarify={(result, description) => prepareForItem(result,
        `Regarding this question: ${result.answer.missing.join("\n")}\n\nMy team's instruction:\n${description.trim()}\n\nPropose a change for my review. Explain its effect and any remaining uncertainty. Check it with Engram before asking me to accept it. This is operator input, not a source quotation.`)}
      onMaterial={async () => { setMaterialReturn({id: draft.id, revision: draft.revision}); await go(1); setNotice("Add the relevant document or sample here, then return to the pack review. Added material does not resolve the issue until the proposal is updated and checked."); }}
    />;
  }

  const resumeLabel = (id: string) => {
    try { return steps[readResumeStep(localStorage.getItem(resumeKey(caps.operator, id)))]; }
    catch { return steps[0]; }
  };
  return (
    <div className="wb">
      <header className="wb-top">
        <a className="wb-brand" href="/workbench.html">
          <Layers3 size={21} /> ENGRAM <span>WORKBENCH</span>
        </a>
        <div>
          <span className="wb-local">Operator · {caps.operator}</span>
          <button
            className="wb-text"
            disabled={busy}
            onClick={() => {
              explanationMemory.current.clear();
              setPreparedRequest(null); setOperatorAnswers({});
              setMaterialReturn(null);
              selection.current++;
              for (const key of Object.keys(sessionStorage)) {
                if (key.startsWith(`engram-edit:${encodeURIComponent(caps.operator)}:`)) sessionStorage.removeItem(key);
              }
              setConflict(null);
              setRecovery(null);
              latest.current = { draft: null, content: null };
              setAuthorPrompt("");
              setError("");
              setNotice("");
              setSourceName("");
              setSourceText("");
              setName("");
              setCreating(false);
              setCaps(null);
              setToken("");
              setDraft(null);
              setContent(null);
              setTenants([]);
              setExported(null);
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="wb-shell">
        <nav className="wb-nav" aria-label="Workspace navigation">
          <button
            className="wb-back"
            disabled={busy || !!running}
            onClick={() =>
              void perform(async () => {
                if (draft) await save();
                selection.current++;
                setDraft(null);
                setContent(null);
                setTenants(await request("/tenants"));
              })
            }
          >
            <ArrowLeft size={16} /> All tenants
          </button>
          <div className="wb-nav-label">
            {context ? content.name : "TENANT DRAFTS"}
          </div>
          {context && !draft.journey && (
            <>
              <span className="wb-env">{content.environment} · draft</span>
              <div className="wb-steps">
                {journey.map((i) => (
                  <button
                    key={i}
                    aria-current={step === i ? "step" : undefined}
                    disabled={busy}
                    onClick={() => void go(i)}
                  >
                    <span>{i === 3 ? "3b" : i < 3 ? i + 1 : i}</span>
                    {steps[i]}
                  </button>
                ))}
              </div>
            </>
          )}
          <div className="wb-nav-footer">
            <ShieldCheck size={20} />
            <strong>Drafts stay separate</strong>
            <p>These are draft workspaces. No live tenant configuration or database is changed here.</p>
            <details><summary>What do these words mean?</summary>
              <dl>
                <dt>Tenant</dt><dd>An isolated Engram environment with its own data and pack configuration. One customer can have multiple tenants, such as development and production.</dd>
                <dt>Tenant draft</dt><dd>A workspace for preparing and testing that configuration. Creating a draft does not provision or activate a runtime.</dd>
                <dt>Pack</dt><dd>Rules describing entities, their identities, events and relationships. A tenant can use several packs.</dd>
                <dt>Event</dt><dd>A report of something that happened in a source system.</dd>
                <dt>Producer</dt><dd>The system sending an event. Trust rules affect how its evidence is used.</dd>
                <dt>Graph</dt><dd>Stored entities and the relationships between them.</dd>
                <dt>Understanding</dt><dd>The agent’s proposed pack, with evidence and assumptions for review.</dd>
                <dt>Story</dt><dd>Prepared events or a saved graph, with expected outcomes to test.</dd>
                <dt>Sandbox</dt><dd>An isolated run of the processing pipeline. Its storage backend is shown with each run; it is not a live tenant deployment.</dd>
                <dt>Answer score</dt><dd>F1 compares expected and returned answers, accounting for missing and unexpected results.</dd>
                <dt>Approval</dt><dd>Review of a specific pack and its evidence for handoff.</dd>
                <dt>Activation</dt><dd>A separate operational procedure, unavailable in this workbench.</dd>
                <dt>Under the hood</dt><dd>Technical details of the pack and its planned updates.</dd>
              </dl>
            </details>
          </div>
        </nav>
        <main className="wb-main">
          {error && (
            <div role="alert" className="wb-error">
              {error}
              {authorFailureDetail && <details><summary>Error details for support</summary><p>{authorFailureDetail}</p></details>}
              <button
                className="wb-text"
                onClick={() =>
                  void perform(async () => {
                    if (draft) {
                      const saved = await request(`/tenants/${draft.id}`);
                      setConflict(saved);
                    }
                  })
                }
              >
                Compare with saved version
              </button>
            </div>
          )}
          {conflict && content && draft && (
            <section className="wb-warning" role="alert">
              <h2>A saved revision needs your review</h2>
              <p>Your typed changes are still here. Saved revision {conflict.revision} differs in: {changedFields(content, conflict.content).join(", ") || "job or review status"}.</p>
              <details><summary>Compare my changes and the saved version</summary>
                <pre>{pretty({myChanges: content, saved: conflict.content})}</pre>
              </details>
              <button onClick={() => {
                const merged = preserveEdits(draft.content, content, conflict.content);
                receive(conflict, undefined, true);
                latest.current = { draft: conflict, content: merged };
                setContent(merged); setConflict(null); setError("");
                setNotice("Your changes are kept locally. Review them, then save against the latest revision.");
              }}>Keep my changes</button>
              <button className="wb-secondary" onClick={() => {
                receive(conflict, undefined, true); setConflict(null); setError("");
              }}>Use the saved version</button>
            </section>
          )}
          {recovery && (
            <section id="workbench-recovery" tabIndex={-1} className="wb-warning" role="status">
              <h2>Restore what you typed?</h2>
              <p>This tab kept unsaved input for this operator and tenant. Recovery is offered for up to 24 hours and cleared on sign out. It uses this browser’s tab session storage; access tokens are not stored.</p>
              <button onClick={() => {
                setContent(recovery.content); latest.current.content = recovery.content;
                setSourceName(recovery.sourceName); setSourceText(recovery.sourceText);
                setSourceKind(recovery.sourceKind); setAuthorPrompt(recovery.authorPrompt);
                setOperatorAnswers(recovery.operatorAnswers || {});
                setReviewTicks(reviewTicksFor(draft!, recovery.reviewTicks || null));
                setPreparedRequest(recovery.authorPrompt.trim() ? {...(recovery.preparedRequest || {itemKey:"recovered", subject:"Recovered request — original issue unavailable", answer:"", proposal:""}), reviewedRevision:null} : null);
                setStep(recovery.authorPrompt.trim() ? 2 : recovery.step); setRecovery(null); focusRequest();
              }}>Restore my input</button>
              <button className="wb-secondary" onClick={() => setRecovery(null)}>Keep the saved version</button>
            </section>
          )}
          {connectionNotice && <p role="status" className="wb-warning">{connectionNotice}</p>}
          {recoveryError && <p role="status">{recoveryError}</p>}
          {notice && (
            <div role="status" className="wb-notice">
              {notice}
            </div>
          )}
          {caps?.sandbox === "spanner" && (
            <section className="wb-card" aria-label="Sandbox database capacity">
              <h2>Sandbox databases</h2>
              <p>{capacityError ? "Availability could not be checked. No memory fallback will be used."
                : !capacity ? "Checking available databases…"
                : `${capacity.available} of ${capacity.capacity} databases available.`}</p>
              {capacity?.available === 0 && <p>All databases are busy or need attention. Wait for cleanup to finish before retrying; a failed example check does not indicate this capacity problem.</p>}
              <p>These databases are reserved for examples, separate from tenant data. Starting a run claims one exclusively; availability may change before your run starts.</p>
              {!!capacity?.slots.length && <details><summary>For engineers: database status</summary>
                <ul>{capacity.slots.map(slot => <li key={slot.resource}><code>{slot.resource}</code> — {slot.state}</li>)}</ul>
              </details>}
            </section>
          )}
          {draft?.storage_run && (
            <section className="wb-notice" role="status" aria-live="polite">
              <strong>Sandbox: {draft.storage_run.backend === "spanner" ? "Spanner database" : "isolated memory"}</strong>
              <p>{draft.job?.cancelling ? "Stopping the run safely. Wait for cleanup before starting again." : ({
                allocating: "Finding an available sandbox database…",
                opening: "Opening the assigned sandbox database…",
                running: "Running the examples and checking their results…",
                cleaning: "Removing this run’s data before the database can be reused…",
                released: "Cleanup verified. The sandbox database is available for reuse.",
              } as Record<string, string>)[draft.storage_run.phase] || "Checking sandbox status…"}</p>
              {draft.storage_run.cleanup === "quarantined_or_unavailable" && <p>Cleanup could not be verified. This database is unavailable for reuse and needs an engineer’s attention.</p>}
              {draft.storage_run.resource && <details><summary>For engineers: assigned database</summary><code>{draft.storage_run.resource}</code></details>}
            </section>
          )}
          {!context ? (
            <>
              <div className="wb-heading">
                <div>
                  <p className="wb-eyebrow">OPERATOR WORKSPACE</p>
                  <h1>Tenants</h1>
                  <p>
                    A pack describes a tenant’s world. Build it from their documents and events, test it with examples, then review it for handoff.
                  </p>
                </div>
                <button onClick={() => setCreating(true)}>
                  <Plus size={16} /> Start a new tenant draft
                </button>
              </div>
              <section className="wb-card">
                <h2>See how a prepared pack behaves</h2>
                <p>
                  Software delivery (PDLC) has prepared stories: saved examples with expected outcomes. Run one without building a pack or calling the agent.
                </p>
                <button
                  disabled={busy}
                  onClick={() =>
                    void perform(async () => {
                      const prepared = await request(
                        "/journeys/implementation",
                        "POST",
                      );
                      await open(prepared.id);
                    })
                  }
                >
                  Was this requirement implemented, reviewed and tested?
                </button>
                <button
                  className="wb-secondary"
                  disabled={busy}
                  onClick={() =>
                    void perform(async () => {
                      const prepared = await request(
                        "/journeys/planning",
                        "POST",
                      );
                      await open(prepared.id);
                    })
                  }
                >
                  Did design approval carry across revisions?
                </button>
                <button
                  className="wb-secondary"
                  disabled={busy}
                  onClick={() =>
                    void perform(async () => {
                      const prepared = await request(
                        "/journeys/release",
                        "POST",
                      );
                      await open(prepared.id);
                    })
                  }
                >
                  Which deployment shipped this change?
                </button>
                <button
                  className="wb-secondary"
                  disabled={busy}
                  onClick={() => void perform(async () => {
                    const prepared = await request("/journeys/references", "POST");
                    await open(prepared.id);
                  })}
                >
                  Where does a reference stop being trustworthy?
                </button>
                <label>More stories about answering questions
                  <select value={retrievalScenario} disabled={busy} onChange={e => setRetrievalScenario(e.target.value)}>
                    <option value="retrieval-trust">What context is current, complete and trusted?</option>
                    <option value="review-verdict">Was the change approved or were changes requested?</option>
                    <option value="trust-corroboration">Is there independent evidence for this claim?</option>
                    <option value="version-precision">Which release does this version refer to?</option>
                    <option value="number-precision">Which change does this number identify?</option>
                    <option value="rare-word">Which change matches these distinctive words?</option>
                    <option value="paging-complete">Are all confirmed tests included across pages?</option>
                    <option value="paging-proposed">Are proposed links still labelled across pages?</option>
                    <option value="paging-truncated">Does Engram tell us when an answer is incomplete?</option>
                    <option value="paging-traversal">Do smaller graph pages preserve the answer?</option>
                    <option value="category-evaluation">How do graph answers compare with text search?</option>
                    <option value="query-budget">Does a long question stay within work limits?</option>
                    <option value="rejected-refinement">Are rejected relationships excluded from the answer?</option>
                  </select>
                </label>
                <button className="wb-secondary" disabled={busy}
                  onClick={() => void perform(async () => {
                    const prepared = await request(`/journeys/${retrievalScenario}`, "POST");
                    await open(prepared.id);
                  })}>
                  Open selected answer story
                </button>
              </section>
              {creating && (
                <form
                  className="wb-card"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void perform(async () => {
                      const created = await request(
                        "/tenants",
                        "POST",
                        initialContent(name.trim(), environment.trim()),
                      );
                      setCreating(false);
                      setName("");
                      await open(created.id);
                    });
                  }}
                >
                  <h2>Create a tenant draft</h2>
                  <div className="wb-grid">
                    <label>
                      Tenant name
                      <input
                        required
                        maxLength={100}
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                      />
                    </label>
                    <label>
                      Environment
                      <input
                        required
                        maxLength={60}
                        value={environment}
                        onChange={(e) => setEnvironment(e.target.value)}
                      />
                    </label>
                  </div>
                  <p className="wb-muted">
                    This creates a local draft workspace. It does not deploy a tenant runtime or create a database.
                  </p>
                  <button
                    disabled={busy || !name.trim() || !environment.trim()}
                  >
                    Create draft
                  </button>
                </form>
              )}
              <div className="wb-tenant-grid">
                {tenants.map((t) => (
                  <button
                    className="wb-tenant"
                    disabled={busy}
                    key={t.id}
                    onClick={() => void perform(() => open(t.id))}
                  >
                    <div>
                      <Layers3 size={20} />
                      <span className="wb-env">{t.content.environment}</span>
                    </div>
                    <h2>{t.content.name}</h2>
                    <p>
                      {t.content.scope ||
                        "Start with scope and source evidence."}
                    </p>
                    {!t.journey && <p>Continue at {resumeLabel(t.id)}</p>}
                    <footer>
                      {t.journey
                        ? t.journey_result_stale
                          ? "Run needs refreshing"
                          : t.journey_result
                            ? t.journey_result.passed
                              ? "Story checks passed"
                              : "Story needs attention"
                            : "Prepared story"
                        : t.approval && t.readiness.approve.ready
                          ? "Approved for handoff"
                          : t.sandbox && !t.sandbox.passed
                            ? "Test needs attention"
                            : t.approval
                              ? "Needs revalidation"
                              : "Draft"}{" "}
                      <ChevronRight size={17} />
                    </footer>
                  </button>
                ))}
              </div>
              {!tenants.length && !creating && (
                <div className="wb-empty">
                  <FileText size={36} />
                  <h2>Your first tenant starts with a draft</h2>
                  <p>
                    Add a domain goal, then bring the documents and events that
                    describe it.
                  </p>
                </div>
              )}
            </>
          ) : draft.journey ? (
            <JourneyWorkspace
              key={draft.id}
              draft={draft}
              model={caps.model}
              explaining={!!caps.explaining}
              askCheck={(index, question, signal) => request(`/tenants/${draft.id}/explain`, "POST", {revision: draft.revision, scope: "failed_check", index, question}, token, signal)}
              allowExplanations={() => void perform(async () => { await save({...draft.content, data_policy: "provider_allowed", redaction_confirmed: true}); })}
              backend={caps.sandbox}
              act={(endpoint, body) =>
                void perform(() => action(endpoint, body))
              }
              busy={busy || !!running}
              run={() => void perform(() => action("journey-run"))}
              cancel={() => void perform(() => action("cancel"))}
            />
          ) : (
            <>
              <div className="wb-heading">
                <div>
                  <p className="wb-eyebrow">
                    {content.name} / {content.environment}
                  </p>
                  <h1>{steps[step]}</h1>
                  <p>
                    {
                      [
                        "What should this tenant track, and what data may we use?",
                        "Give the agent the material it needs. Each source is saved when you add it.",
                        "Review what the agent understood, where each idea came from and what still needs your decision.",
                        "For engineers: trace an example event through its contract and planned graph updates.",
                        "Write the tenant’s questions and choose the right answers before testing.",
                        "Run your examples in isolation and see what passed or needs correction.",
                        "Approve the reviewed pack and its test evidence. Nothing changes in production.",
                      ][step]
                    }
                  </p>
                </div>
                <button
                  className="wb-secondary"
                  disabled={!dirty || busy || !!running}
                  onClick={() =>
                    void perform(async () => {
                      await save();
                    })
                  }
                >
                  {busy
                    ? "Saving…"
                    : dirty
                      ? "Save changes"
                      : `Saved · draft revision ${draft.revision}`}
                </button>
              </div>
              {next && (
                <section className="wb-next" aria-label="Next action">
                  <div>
                    <span className="wb-eyebrow">
                      {running ? "TASK IN PROGRESS" : "NEXT ACTION"}
                    </span>
                    <h2>
                      {running
                        ? draft.job?.kind === "author"
                          ? "The agent is preparing your pack"
                          : "Your examples are running"
                        : next.title}
                    </h2>
                    <p>
                      {running
                        ? "You can browse the saved draft while this task runs. Editing is paused to keep the result tied to these inputs."
                        : next.reason}
                    </p>
                    {!running && step === 2 && !!draft.proposal?.limitations.length && next.step !== 2 && <p>You can answer the review items below now. The setup step above is still needed before you can finish testing and approval; answering alone does not complete it.</p>}
                  </div>
                  {!running && next.step !== step && (
                    <button onClick={() => void go(next.step)}>
                      Go to {steps[next.step].toLowerCase()}
                    </button>
                  )}
                  {running && (
                    <button
                      className="wb-secondary"
                      onClick={() => void perform(() => action("cancel"))}
                    >
                      Cancel task
                    </button>
                  )}
                </section>
              )}
              <details className="wb-readiness-details">
                <summary>Full readiness checklist</summary>
                {next && <p><strong>Next action: {running ? "Wait for the current task or cancel it" : next.title}</strong><br />{running ? "The saved draft remains available while the task runs." : next.reason}</p>}
                <div className="wb-readiness" aria-label="Readiness checklist">
                  {(["begin", "run", "approve"] as const).map((tier) => (
                    <details key={tier}>
                      <summary>
                        <span
                          className={
                            draft.readiness[tier].ready && !dirty
                              ? "wb-check"
                              : "wb-pending"
                          }
                        >
                          {draft.readiness[tier].ready && !dirty ? (
                            <Check size={14} />
                          ) : (
                            "○"
                          )}
                        </span>
                        {tier === "begin"
                          ? "Ready to build"
                          : tier === "run"
                            ? "Ready to test"
                            : "Ready to hand off"}
                        <span>
                          {dirty
                            ? "Save changes to refresh"
                            : draft.readiness[tier].ready
                              ? "Ready"
                              : `${draft.readiness[tier].missing.length} to resolve`}
                        </span>
                      </summary>
                      <ul>
                        {draft.readiness[tier].missing.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </details>
                  ))}
                </div>
              </details>
              <fieldset disabled={!!running || !!conflict || !!recovery} className="wb-fields">
                {step === 0 && (
                  <>
                    <section className="wb-card">
                      <h2>What should this pack cover?</h2>
                      <label>
                        Domain scope
                        <textarea
                          value={content.scope}
                          onChange={(e) => patch({ scope: e.target.value })}
                          placeholder="Describe what this tenant needs to track, and what is outside the scope."
                          rows={4}
                          maxLength={4000}
                        />
                      </label>
                      <details>
                        <summary>
                          Advanced · existing packs and optional roots
                        </summary>
                        <p>
                          Core is required. Optional roots and existing domain
                          packs are checked together with your new pack.
                        </p>
                        <div className="wb-inline">
                          <span className="wb-pill">core · required</span>
                          {["memory", "user"].map((root) => (
                            <label className="wb-checkbox" key={root}>
                              <input
                                type="checkbox"
                                checked={content.roots.includes(root)}
                                onChange={(e) =>
                                  patch({
                                    roots: e.target.checked
                                      ? [...content.roots, root]
                                      : content.roots.filter((x) => x !== root),
                                  })
                                }
                              />
                              {root === "memory" ? "Memory — beliefs, goals and episodes" : "User — profiles, preferences and skills"}
                            </label>
                          ))}
                          {(caps.pack_catalog || []).map((pack) => (
                            <label className="wb-checkbox" key={pack.name}>
                              <input
                                type="checkbox"
                                checked={content.existing_packs.includes(pack.name)}
                                onChange={(e) => patch({existing_packs: e.target.checked
                                  ? [...content.existing_packs, pack.name]
                                  : content.existing_packs.filter(name => name !== pack.name)})}
                              />
                              {pack.name} — {pack.description}
                            </label>
                          ))}
                          {!caps.pack_catalog && <p>Pack selection is unavailable from this server. Existing selections are preserved.</p>}

                        </div>
                      </details>
                    </section>
                    <section className="wb-card">
                      <div className="wb-card-title">
                        <ShieldCheck />
                        <h2>Data handling comes first</h2>
                      </div>
                      <p>
                        Sources are saved in this operator workspace. Nothing is
                        sent to the agent’s external service until you permit it and explicitly
                        request a proposal.
                      </p>
                      <label>
                        Permission to use the agent
                        <select
                          value={content.data_policy}
                          onChange={(e) =>
                            patch({
                              data_policy: e.target
                                .value as Content["data_policy"],
                            })
                          }
                        >
                          <option value="undecided">Choose a policy</option>
                          <option value="local_only">
                            Keep inputs local — do not call the agent
                          </option>
                          <option value="provider_allowed">
                            Allow the agent to use these inputs
                          </option>
                        </select>
                      </label>
                      <details className="wb-muted"><summary>Authoring service — technical details</summary>
                        {caps.model || "Not configured. Agent authoring is unavailable."}
                      </details>
                      <label className="wb-checkbox">
                        <input
                          type="checkbox"
                          checked={content.redaction_confirmed}
                          onChange={(e) =>
                            patch({ redaction_confirmed: e.target.checked })
                          }
                        />
                        I reviewed these inputs for sensitive data and removed
                        secrets.
                      </label>
                    </section>
                    <section className="wb-card">
                      <h2>Which sources should this test trust?</h2>
                      <p>
                        Choose which producers in your sample events should be
                        trusted for this test. This grants no production access.
                        Leaving all unchecked means all sources are untrusted.
                      </p>
                      {producers.map((id) => (
                        <label className="wb-checkbox" key={id}>
                          <input
                            type="checkbox"
                            checked={content.trusted_ids.includes(id)}
                            onChange={(e) =>
                              patch({
                                producer_ids: [
                                  ...new Set([...content.producer_ids, id]),
                                ],
                                trusted_ids: e.target.checked
                                  ? [...content.trusted_ids, id]
                                  : content.trusted_ids.filter((x) => x !== id),
                                trust_reviewed: false,
                              })
                            }
                          />
                          Trust {id} in this test
                        </label>
                      ))}
                      {!producers.length && (
                        <p>
                          No producer identities were found in the sample
                          events. Add the producer to the sample envelope or
                          declare it below.
                        </p>
                      )}
                      <details>
                        <summary>
                          Advanced · declare producer identifiers
                        </summary>
                        <label>
                          Producer identifiers
                          <ListInput
                            values={content.producer_ids}
                            onChange={(e) =>
                              patch({
                                producer_ids: split(e.target.value),
                                trust_reviewed: false,
                              })
                            }
                          />
                        </label>
                      </details>
                      <label className="wb-checkbox">
                        <input
                          type="checkbox"
                          checked={content.trust_reviewed}
                          onChange={(e) =>
                            patch({ trust_reviewed: e.target.checked })
                          }
                        />
                        I reviewed how source trust will affect answers.
                      </label>
                    </section>
                  </>
                )}
                {step === 1 && (
                  <>
                    {materialReturn?.id === draft.id && <section className="wb-card">
                      <p>{materialReturn.revision === draft.revision && !dirty ? "Your question and explanation are saved while you add material." : "The draft has changed. Return to the review and ask for a fresh explanation using the updated material."}</p>
                      <button type="button" onClick={() => void go(2)}>Return to the question review</button>
                    </section>}
                    <details
                      className="wb-card wb-source-add"
                      open
                    >
                      <summary>
                        {content.sources.length
                          ? "Add another source"
                          : "Add your first source"}
                      </summary>

                      <p>
                        <strong>
                          1. Choose a file or paste text. 2. Confirm its
                          category. 3. Add and save it.
                        </strong>
                      </p>
                      <p>
                        Specifications explain the domain. Schemas describe
                        available fields. Samples show actual values. You can
                        add any of them first.
                      </p>
                      <label className="wb-file">
                        Choose a text, Markdown or JSON file to preview (PDF is not supported)
                        <input
                          aria-label="Upload grounding source"
                          type="file"
                          accept=".txt,.md,.json"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              if (file.size > 160000) {
                                setError("File exceeds the intake limit.");
                                return;
                              }
                              void file.text().then((text) => {
                                setSourceText(text);
                                setSourceName(file.name);
                                const suggestion = suggestCategory(text);
                                if (suggestion.kind) setSourceKind(suggestion.kind);
                                setNotice(
                                  "File loaded for preview. Confirm the source category, then click Add and save source.",
                                );
                              });
                            }
                            e.target.value = "";
                          }}
                        />
                      </label>
                      <div className="wb-grid">
                        <label>
                          Source category
                          <select
                            value={sourceKind}
                            onChange={(e) =>
                              setSourceKind(e.target.value as Source["kind"])
                            }
                          >
                            <option value="specification">
                              Process document / glossary
                            </option>
                            <option value="schema">
                              Interface schema (JSON)
                            </option>
                            <option value="samples">
                              Sample events (JSON)
                            </option>
                          </select>
                        </label>
                        <label>
                          Source name
                          <input
                            value={sourceName}
                            maxLength={160}
                            onChange={(e) => { setSourceName(e.target.value); setNotice(""); }}
                            placeholder="Process guide · relevant section"
                          />
                        </label>
                      </div>
                      <label>
                        Contents
                        <textarea
                          rows={9}
                          value={sourceText}
                          onChange={(e) => { setSourceText(e.target.value); setNotice(""); }}
                          placeholder={
                            sourceKind === "samples"
                              ? "Paste representative JSON events from this tenant’s source system."
                              : "Paste source material here…"
                          }
                        />
                      </label>
                      {sourceText.trim() && <div role="status">
                        <p>{suggestCategory(sourceText).reason} This suggestion uses only the format of your material.</p>
                        {suggestCategory(sourceText).kind && suggestCategory(sourceText).kind !== sourceKind && <button type="button" className="wb-secondary" onClick={() => setSourceKind(suggestCategory(sourceText).kind!)}>Use suggested category: {sourceLabels[suggestCategory(sourceText).kind!]}</button>}
                        {suggestCategory(sourceText).kind === sourceKind && <p>Suggested category matches your selection: {sourceLabels[sourceKind]}.</p>}
                      </div>}
                      <div className="wb-inline">

                        <button
                          disabled={busy || !!running}
                          onClick={() => void perform(addSource)}
                        >
                          <Plus size={16} /> Add and save source
                        </button>
                      </div>
                      <p className="wb-muted">
                        Up to 20 sources, 40,000 characters each, and 100
                        events. Sample envelope: event_type, payload, optional
                        producer_id, occurred_at, event_id and expect_admitted
                        (false for a rejection case).
                      </p>
                    </details>
                    <IntakeEvidence key={draft.id} revision={draft.revision} dirty={dirty} load={() => request(`/tenants/${draft.id}/evidence`, "GET", undefined, token)} />
                    <section className="wb-card">
                      <h2>
                        Evidence inventory{" "}
                        <span className="wb-count">
                          {content.sources.length}
                        </span>
                      </h2>
                      {content.sources.length === 0 && (
                        <p>
                          No evidence yet. You do not need a formal
                          specification if schemas, samples and a domain
                          explanation establish the scope.
                        </p>
                      )}
                      {content.sources.map((source) => (
                        <details key={source.id} className="wb-source">
                          <summary>
                            <FileText size={16} />
                            {source.name}
                            <span className="wb-pill">{source.kind}</span>
                          </summary>
                          <label>
                            Category for {source.name}
                            <select
                              value={source.kind}
                              onChange={(e) => {
                                const kind = e.target.value as Source["kind"];
                                void perform(() =>
                                  save({
                                    ...content,
                                    sources: content.sources.map((s) =>
                                      s.id === source.id ? { ...s, kind } : s,
                                    ),
                                  }).then(() => {}),
                                );
                              }}
                            >
                              <option value="specification">
                                Process document / glossary
                              </option>
                              <option value="schema">
                                Interface schema (JSON)
                              </option>
                              <option value="samples">
                                Sample events (JSON)
                              </option>
                            </select>
                          </label>
                          <pre>{source.text}</pre>
                          <button
                            className="wb-text"
                            onClick={() =>
                              patch({
                                sources: content.sources.filter(
                                  (s) => s.id !== source.id,
                                ),
                              })
                            }
                          >
                            Remove from draft
                          </button>
                        </details>
                      ))}
                    </section>
                  </>
                )}
                {step === 2 && (
                  <>
                    {!visibleRequestOwner && renderRequestReview()}
                    <ModelReview
                      draft={draft}
                      content={content}
                      busy={busy}
                      dirty={dirty}
                      reviewTicks={reviewTicksFor(draft, reviewTicks)}
                      onReviewTicks={setReviewTicks}
                      explain={renderExplanation}
                      onDecision={(id, value) => {
                        const decisions = { ...content.decisions };
                        if (value.trim()) decisions[id] = value;
                        else delete decisions[id];
                        patch({ decisions });
                      }}
                      onAddMaterial={() => void go(1)}
                      onApplyAnswers={() => void authorModel()}
                      onKeepRemoved={() => {
                        if (authorPrompt.trim()) {
                          if (!preparedRequest) setPreparedRequest({itemKey: "existing-request", subject: "Your existing revision request", answer: "", reviewedRevision: null, proposal: JSON.stringify(draft.proposal)});
                          focusRequest(); return;
                        }
                        const items = draft.proposal?.repair_removals || [];
                        const subject = `Keep removed items: ${items.join(", ")}`;
                        const itemKey = answerKey(draft.id, "removals", subject);
                        const answer = `Keep these items: ${items.join(", ")}.`;
                        setOperatorAnswers(values => ({...values, [itemKey]: answer}));
                        setPreparedRequest({itemKey, subject, answer, reviewedRevision: draft.revision, proposal: JSON.stringify(draft.proposal)});
                        setAuthorPrompt(`${answer}\n\nPropose restoring them for my review. Do not silently remove other data to pass validation. Explain anything that cannot be retained and why. Nothing is approved by this request.`);
                        focusRequest();
                      }}
                      onAccept={(accepted_removals, accepted_changes, confirmed_policies) =>
                        void perform(() =>
                          action("review", {
                            accepted_removals,
                            accepted_changes,
                            confirmed_policies,
                            accepted_facts: facts.map((f) => f.id),
                            rejected_facts: [],
                            pack_accepted: true,
                          }),
                        )
                      }
                      onValidate={() => void perform(() => action("validate"))}
                      onReject={(id) =>
                        void perform(() =>
                          action("review", {
                            accepted_facts: reviewed.filter((x) => x !== id),
                            rejected_facts: rejected.includes(id)
                              ? rejected.filter((x) => x !== id)
                              : [...rejected, id],
                            pack_accepted: false,
                          }),
                        )
                      }
                    />
                    <AuthorSession
                      draft={draft}
                      content={content}
                      caps={caps}
                      busy={busy}
                      prompt={authorPrompt}
                      setPrompt={setAuthorPrompt}
                      onAuthor={() => void authorModel()}
                      onCancel={() => void perform(() => action("cancel"))}
                      requestReviewActive={!!preparedRequest && !!authorPrompt.trim()} onReviewRequest={focusRequest}
                      explainFailure={renderExplanation("author_error", 0)}
                    />
                  </>
                )}
                {(step === 2 || step === 3) && (
                  <details className="wb-technical" open={step === 3 ? true : undefined}>
                    <summary>
                      For engineers · contracts, event rules and planned updates
                    </summary>
                    <section className="wb-card">
                      <h2>Pack proposal</h2>
                      {!pack ? (
                        <p>
                          Conceptual draft. Add schemas, sample events and
                          identity decisions, then request an executable
                          proposal.
                        </p>
                      ) : (
                        <>
                          <div className="wb-inline">
                            <span className="wb-pill">
                              {pack.pack?.name} · {pack.pack?.version}
                            </span>
                            <span>
                              Requires {(pack.pack?.requires || []).join(", ")}
                            </span>
                          </div>
                          <PackGraph
                            mode="schema"
                            nodes={Object.entries<any>(
                              pack.types?.nodes || {},
                            ).map(([id, properties]) => ({
                              id,
                              type: id,
                              properties,
                            }))}
                            edges={Object.entries<any>(
                              pack.types?.edges || {},
                            ).flatMap(([type, edge]) =>
                              (edge.from || []).flatMap((source: string) =>
                                (edge.to || []).map((target: string) => ({
                                  source,
                                  target,
                                  type,
                                })),
                              ),
                            )}
                          />
                          <h3>Types and lifecycle</h3>
                          <div className="wb-model">
                            {Object.entries<any>(pack.types?.nodes || {}).map(
                              ([type, def]) => (
                                <article key={type}>
                                  <strong>{type}</strong>
                                  <p>Key: {def.key?.join(" + ")}</p>
                                  <small>
                                    {Object.keys(def.properties || {}).join(
                                      ", ",
                                    )}
                                  </small>
                                  {def.lifecycle && (
                                    <p>
                                      States: {def.lifecycle.states?.join(", ")}
                                      <br />
                                      Initial: {def.lifecycle.initial}
                                    </p>
                                  )}
                                </article>
                              ),
                            )}
                          </div>
                          {(pack.projection || [])
                            .filter((rule: any) => rule.transition)
                            .map((rule: any, index: number) => (
                              <p key={index} className="wb-muted">
                                {rule.event}: {rule.transition.type} ·{" "}
                                {(rule.transition.only_from?.length
                                  ? rule.transition.only_from
                                  : ["any allowed state"]
                                ).join(", ")}{" "}
                                → {rule.transition.to}
                              </p>
                            ))}
                          <h3>Relationships</h3>
                          {Object.entries<any>(pack.types?.edges || {}).map(
                            ([type, edge]) => (
                              <p key={type}>
                                {edge.from?.join(", ")} {" "}
                                <strong>{type.split("_").join(" ").toLowerCase()}</strong> {" "} {edge.to?.join(", ")}
                              </p>
                            ),
                          )}
                          <h3>Declared event contracts</h3>
                          {Object.entries<any>(pack.events || {}).map(
                            ([type, def]) => (
                              <details className="wb-source" key={type}>
                                <summary>
                                  {type}
                                  <span className="wb-pill">
                                    {def.handling || "processed (default)"}
                                  </span>
                                </summary>
                                <pre>
                                  {pretty(
                                    def.payload_contract || "Missing contract",
                                  )}
                                </pre>
                              </details>
                            ),
                          )}
                          <p>Review and accept the pack in “How Engram understands them”, including its changes and policy confirmations.</p>
                          <button
                            disabled={
                              dirty || busy || !!running || draft.proposal_stale
                            }
                            onClick={() =>
                              void perform(() => action("validate"))
                            }
                          >
                            Validate with Engram
                          </button>
                        </>
                      )}
                    </section>
                    {draft.validation && (
                      <section className="wb-card">
                        <h2>
                          {draft.validation.passed
                            ? "Engine checks passed"
                            : "Engine checks need attention"}
                        </h2>
                        {draft.validation.problems.map((p, i) => (
                          <p className="wb-error" key={i}>
                            {p}
                          </p>
                        ))}
                        {draft.validation.inert?.map((p, i) => (
                          <p className="wb-warning" key={i}>
                            Loaded but inactive: {p}
                          </p>
                        ))}
                        <label>
                          Sample to inspect
                          <select
                            value={selectedEvent}
                            onChange={(e) =>
                              setSelectedEvent(Number(e.target.value))
                            }
                          >
                            {draft.validation.samples?.map((s, i) => (
                              <option key={i} value={i}>
                                {i + 1}. {s.event_type}
                              </option>
                            ))}
                          </select>
                        </label>
                        {draft.validation.samples?.[selectedEvent] && (
                          <>
                            <MappingEvidence
                              sample={draft.validation.samples[selectedEvent]}
                            />
                            <div className="wb-grid">
                              <div>
                                <h3>Admission</h3>
                                <pre>
                                  {pretty(
                                    draft.validation.samples[selectedEvent]
                                      .admission,
                                  )}
                                </pre>
                              </div>
                              <div>
                                <h3>Planned graph delta</h3>
                                <pre>
                                  {pretty(
                                    draft.validation.samples[selectedEvent]
                                      .planned,
                                  )}
                                </pre>
                              </div>
                            </div>
                            <p className="wb-muted">
                              Planned writes have not been committed. Use
                              Evaluation to inspect the observed graph.
                            </p>
                          </>
                        )}
                      </section>
                    )}
                  </details>
                )}
                {step === 4 && (
                  <>
                    <section className="wb-card">
                      <div className="wb-card-title">
                        <h2>Questions and expected answers</h2>
                        <button
                          className="wb-secondary"
                          onClick={() =>
                            patch({
                              questions: [
                                ...content.questions,
                                {
                                  id: `q-${crypto.randomUUID().slice(0, 8)}`,
                                  query: "",
                                  expected: [],
                                  intent: null,
                                  seed_node_ids: [],
                                  seed_mode: "discover",
                                  node_type: null,
                                  reviewed: false,
                                  expectation_statement: "",
                                },
                              ],
                            })
                          }
                        >
                          <Plus size={16} /> Add question
                        </button>
                      </div>
                      <p>
                        Write the business question and establish its answer from the source material first.
                        Then select the matching entities from the examples. Generated entities are candidates,
                        not proof that an answer is correct. Check that separate records have not been combined.
                      </p>
                      {content.questions.map((q, i) => {
                        const update = (change: object) =>
                          patch({
                            questions: content.questions.map((x, n) =>
                              n === i ? { ...x, ...change } : x,
                            ),
                          });
                        return (
                          <div className="wb-question" key={q.id}>
                            <label>
                              Question {i + 1}
                              <textarea
                                rows={2}
                                value={q.query}
                                onChange={(e) =>
                                  update({
                                    query: e.target.value,
                                    reviewed: false,
                                  })
                                }
                                placeholder="What does the tenant need to find out?"
                              />
                            </label>
                            <label>
                              Expected business outcome
                              <small>Write the answer in business terms using the specification or an operator decision, before choosing generated entities. Include the source or reason.</small>
                              <textarea rows={3} value={q.expectation_statement || ""}
                                onChange={e => update({expectation_statement: e.target.value, reviewed: false})}
                                placeholder="Describe the correct answer and the source or team decision that establishes it." />
                            </label>
                            <EntityPicker
                              label="Expected answers"
                              options={entities.filter(
                                (e) => !q.node_type || e.type === q.node_type,
                              )}
                              selected={q.expected}
                              disabled={!!draft.proposal_stale}
                              onChange={(ids) =>
                                update({ expected: ids, reviewed: false })
                              }
                            />
                            <details>
                              <summary>
                                Starting point (optional)
                                {q.seed_node_ids.length
                                  ? ` · ${entities.length ? q.seed_node_ids.map(entityLabel).join(", ") : `${q.seed_node_ids.length} saved selection(s), available after validation`}`
                                  : ""}
                              </summary>
                              <EntityPicker
                                label="Start from these entities"
                                options={entities}
                                selected={q.seed_node_ids}
                                disabled={!!draft.proposal_stale}
                                onChange={(ids) =>
                                  update({
                                    seed_node_ids: ids,
                                    reviewed: false,
                                  })
                                }
                              />
                              <label className="wb-check">
                                <input
                                  type="checkbox"
                                  checked={q.seed_mode === "explicit"}
                                  disabled={!!draft.proposal_stale || (!q.seed_node_ids.length && q.seed_mode !== "explicit")}
                                  onChange={(e) => update({
                                    seed_mode: e.target.checked ? "explicit" : "discover",
                                    reviewed: false,
                                  })}
                                />
                                Only start from the entities I selected
                              </label>
                              <p className="wb-muted">
                                {q.seed_mode === "explicit"
                                  ? "Every selected entity must exist. Engram follows its relationships without finding extra starting points in the question. Connected entities may still belong to other accounts."
                                  : "Engram can also find starting points from words in your question."}
                              </p>
                              {q.seed_mode === "explicit" && !q.seed_node_ids.length && (
                                <p className="wb-error">Choose a starting entity or turn off this option before running the question.</p>
                              )}
                            </details>
                            <details>
                              <summary>
                                Technical details · internal IDs
                              </summary>{" "}
                              <div className="wb-grid">
                                <label>
                                  Retrieval intent
                                  <select
                                    value={q.intent || ""}
                                    onChange={(e) =>
                                      update({
                                        intent: e.target.value || null,
                                        reviewed: false,
                                      })
                                    }
                                  >
                                    <option value="">
                                      Choose automatically
                                    </option>
                                    {Object.keys(
                                      pack?.retrieval?.intents || {},
                                    ).map((name) => (
                                      <option key={name} value={name}>
                                        {name.replace(/_/g, " ")}
                                      </option>
                                    ))}
                                    {q.intent &&
                                      !pack?.retrieval?.intents?.[q.intent] && (
                                        <option value={q.intent}>
                                          {q.intent} (awaiting proposal)
                                        </option>
                                      )}
                                  </select>
                                </label>
                                <label>
                                  Answer type
                                  <select
                                    value={q.node_type || ""}
                                    onChange={(e) =>
                                      update({
                                        node_type: e.target.value || null,
                                        reviewed: false,
                                      })
                                    }
                                  >
                                    <option value="">Any type</option>
                                    {Object.keys(pack?.types?.nodes || {}).map(
                                      (name) => (
                                        <option key={name}>{name}</option>
                                      ),
                                    )}
                                    {q.node_type &&
                                      !pack?.types?.nodes?.[q.node_type] && (
                                        <option>{q.node_type}</option>
                                      )}
                                  </select>
                                </label>
                              </div>
                              <p>
                                The engine derives these IDs from the pack's key
                                rules. Use the selectors above for routine
                                review.
                              </p>
                              <label>
                                Expected node IDs
                                <ListInput
                                  values={q.expected}
                                  onChange={(e) =>
                                    update({
                                      expected: split(e.target.value),
                                      reviewed: false,
                                    })
                                  }
                                />
                              </label>
                              <label>
                                Seed node IDs
                                <ListInput
                                  values={q.seed_node_ids}
                                  onChange={(e) =>
                                    update({
                                      seed_node_ids: split(e.target.value),
                                      reviewed: false,
                                    })
                                  }
                                />
                              </label>
                              <label>
                                Intent identifier
                                <input
                                  value={q.intent || ""}
                                  onChange={(e) =>
                                    update({
                                      intent: e.target.value || null,
                                      reviewed: false,
                                    })
                                  }
                                />
                              </label>
                            </details>
                            <div className="wb-inline">
                              <label className="wb-checkbox">
                                <input
                                  type="checkbox"
                                  disabled={q.expectation_statement != null && !q.expectation_statement.trim()}
                                  checked={q.reviewed}
                                  onChange={(e) =>
                                    update({ reviewed: e.target.checked })
                                  }
                                />
                                Expected answer reviewed
                              </label>
                              <button
                                className="wb-text"
                                onClick={() =>
                                  patch({
                                    questions: content.questions.filter(
                                      (_, n) => n !== i,
                                    ),
                                  })
                                }
                              >
                                Remove question
                              </button>
                            </div>
                          </div>
                        );
                      })}
                      <details>
                        <summary>Advanced · test pass threshold</summary>
                        <p>
                          F1 balances missing answers and unexpected answers. A
                          score of 1 requires the expected set exactly.
                        </p>
                        <label>
                          Required mean F1
                          <input
                            type="number"
                            min={0}
                            max={1}
                            step={0.05}
                            value={content.min_f1}
                            onChange={(e) =>
                              patch({ min_f1: Number(e.target.value) })
                            }
                          />
                        </label>
                      </details>
                    </section>
                    <section className="wb-card">
                      <h2>Expected graph outcomes</h2>
                      <p>
                        Select the entities that these examples must create.
                        Rejected sample events are checked from their expected
                        handling.
                      </p>
                      <EntityPicker
                        label="Entities that must exist"
                        options={entities}
                        selected={content.expected_nodes}
                        onChange={(ids) =>
                          patch({ expected_nodes: ids, graph_reviewed: false })
                        }
                      />
                      <details>
                        <summary>Advanced graph checks · internal IDs</summary>
                        <label>
                          Required node IDs
                          <ListInput
                            values={content.expected_nodes}
                            onChange={(e) =>
                              patch({
                                expected_nodes: split(e.target.value),
                                graph_reviewed: false,
                              })
                            }
                          />
                        </label>
                        <label>
                          Forbidden node IDs
                          <ListInput
                            values={content.forbidden_nodes}
                            onChange={(e) =>
                              patch({
                                forbidden_nodes: split(e.target.value),
                                graph_reviewed: false,
                              })
                            }
                          />
                        </label>
                      </details>
                      <label className="wb-checkbox">
                        <input
                          type="checkbox"
                          checked={content.graph_reviewed}
                          onChange={(e) =>
                            patch({ graph_reviewed: e.target.checked })
                          }
                        />
                        I reviewed these graph expectations before execution.
                      </label>
                    </section>

                  </>
                )}
                {step === 5 && (
                  <>
                    {!draft.sandbox && draft.previous_sandbox && (
                      <section className="wb-card">
                        <h2>
                          Previous test result · revision{" "}
                          {draft.previous_sandbox.revision}
                        </h2>
                        <p>
                          {draft.previous_sandbox.result.passed
                            ? "Previously passed"
                            : "Previously failed"}
                          . This evidence is retained for comparison; it does
                          not approve the current revision.
                        </p>
                        <details>
                          <summary>
                            Previous expected and retrieved results
                          </summary>
                          <pre>
                            {pretty(draft.previous_sandbox.result.evaluation)}
                          </pre>
                        </details>
                      </section>
                    )}
                    <section className="wb-card">
                      <h2>Run the tenant examples</h2>
                      <p>
                        {caps?.sandbox === "spanner"
                          ? "Run the examples through Engram’s processing pipeline on a dedicated Spanner sandbox database, then answer your reviewed questions. The database is cleaned before reuse. This does not activate a tenant."
                          : "Run the examples through Engram’s processing pipeline in isolated memory, then answer your reviewed questions. This does not test a live database or activate a tenant."}
                      </p>
                      {content.expected_nodes.length > 0 && !content.graph_reviewed && (
                        <p role="status">Your graph selections are saved, but their review is not confirmed. Go to Questions to answer, review the saved selections and tick “I reviewed these graph expectations before execution.” Then continue here to run them.</p>
                      )}
                      <button
                        disabled={
                          dirty ||
                          busy ||
                          !!running ||
                          !draft.readiness.run.ready
                        }
                        onClick={() => void perform(() => action("sandbox"))}
                      >
                        Run the examples
                      </button>
                      <button className="wb-secondary"
                        disabled={busy || !!running || dirty || !!draft.proposal_stale || !!draft.pending_decisions || !draft.validation?.passed || !draft.review?.pack_accepted}
                        onClick={() => void perform(() => action("story-workspace"))}>
                        Create a story workspace for this pack
                      </button>
                      <p>This pins the current pack and its dependencies in a separate workspace. The agent can then propose events and checks; you review the expectations before running them.</p>
                      {!draft.readiness.run.ready && (
                        <p className="wb-muted">
                          Open the full readiness checklist above to see what
                          remains.
                        </p>
                      )}
                    </section>
                    {draft.sandbox && (
                      <>
                        <section className="wb-card">
                          <h2>
                            {draft.sandbox.passed
                              ? "Example checks passed"
                              : "Examples need attention"}
                          </h2>
                          <p>
                            Storage for this recorded run: {draft.sandbox.backend === "spanner" ? "Spanner" : draft.sandbox.backend === "isolated-memory" ? "isolated memory" : "not recorded"}.
                          </p>
                          <p>
                            Average answer score (F1): {(100 * draft.sandbox.evaluation.mean_f1).toFixed(1)}% ·
                            Required: {(100 * draft.sandbox.evaluation.min_f1).toFixed(1)}%
                          </p>
                          <p>
                            This compares the actual answers with the reviewed answers, not just their counts. The gate uses the average score across questions; question execution errors, missing or forbidden entities, and processing failures also block approval.
                          </p>
                          <div className="wb-table-scroll">
                            <table>
                              <thead>
                                <tr>
                                  <th>Question</th>
                                  <th>Expected</th>
                                  <th>Retrieved</th>
                                  <th>Answer match</th>
                                </tr>
                              </thead>
                              <tbody>
                                {draft.sandbox.evaluation.questions?.map(
                                  (r: any) => (
                                    <tr key={r.id}>
                                      <td>
                                        {content.questions.find(
                                          (q) => q.id === r.id,
                                        )?.query || r.id}
                                      </td>
                                      <td>
                                        {r.expected
                                          .map(entityLabel)
                                          .join("; ") || "None"}
                                      </td>
                                      <td>
                                        {r.found.map(entityLabel).join("; ") ||
                                          "None"}
                                      </td>
                                      <td>{r.error
                                        ? <span className="wb-error">Could not run this question: {r.error}</span>
                                        : <>{r.f1 === 1 ? "Exact match" : "Differs from expected"} · {(r.f1 * 100).toFixed(1)}%</>}</td>
                                    </tr>
                                  ),
                                )}
                              </tbody>
                            </table>
                          </div>
                          {!!draft.sandbox.missing_nodes.length && (
                            <p className="wb-error">
                              Expected entities not found:{" "}
                              {draft.sandbox.missing_nodes.map(entityLabel).join(", ")}
                            </p>
                          )}
                          {!!draft.sandbox.forbidden_nodes.length && (
                            <p className="wb-error">
                              These entities should not have been created:{" "}
                              {draft.sandbox.forbidden_nodes.map(entityLabel).join(", ")}
                            </p>
                          )}
                          {!draft.sandbox.passed && (
                            <div className="wb-warning">
                              <strong>
                                Approval is blocked until these checks pass.
                              </strong>
                              <p>
                                {sandboxGuidance(draft.sandbox).reason}
                              </p>
                              <button className="wb-secondary" onClick={() => void go(sandboxGuidance(draft.sandbox).step)}>
                                {sandboxGuidance(draft.sandbox).title}
                              </button>
                              <button
                                className="wb-secondary"
                                onClick={() => {
                                  setAuthorPrompt(
                                    "Investigate the failed evaluation. First check question configuration: answer type, starting entities and search mode. Keep reviewed expected answers unchanged. If question settings are correct, explain what source-grounded pack correction or engineering investigation is needed. Do not invent configuration options.",
                                  );
                                  void go(2);
                                }}
                              >
                                Discuss this failure with the agent
                              </button>
                            </div>
                          )}
                          <details>
                            <summary>Execution limits</summary>
                            <ul>
                              {draft.sandbox.limits.map((l) => (
                                <li key={l}>{l}</li>
                              ))}
                            </ul>
                          </details>
                        </section>
                        <section className="wb-card">
                          <h2>Observed graph, event by event</h2>
                          <label>
                            Executed event
                            <select
                              value={selectedEvent}
                              onChange={(e) =>
                                setSelectedEvent(Number(e.target.value))
                              }
                            >
                              {draft.sandbox.steps.map((s, i) => (
                                <option key={i} value={i}>
                                  {i + 1}. {s.event_type} ·{" "}
                                  {s.admitted ? "admitted" : "rejected"}
                                </option>
                              ))}
                            </select>
                          </label>
                          <ObservedGraph
                            step={draft.sandbox.steps[selectedEvent]}
                          />
                        </section>
                      </>
                    )}
                  </>
                )}
                {step === 6 && (
                  <>
                    <section className="wb-card">
                      <h2>Approval for handoff</h2>
                      {draft.validation?.change && (
                        <p>
                          Engine change class:{" "}
                          <strong>{draft.validation.change.kind}</strong> · New
                          tenant draft; no existing live graph is being changed.
                        </p>
                      )}
                      {draft.validation?.packs && (
                        <p className="wb-muted">
                          Composed bundle:{" "}
                          {draft.validation.packs
                            .map((p) => `${p.name} ${p.version}`)
                            .join(" · ")}
                        </p>
                      )}
                      {draft.validation?.engine_revision && (
                        <details>
                          <summary>Verified engine and inputs</summary>
                          <p className="wb-muted">
                            Engine:{" "}
                            <code>{draft.validation.engine_revision}</code>
                          </p>
                          <p className="wb-muted">
                            Inputs: <code>{draft.validation.input_digest}</code>
                          </p>
                        </details>
                      )}
                      <p>
                        Approval pins this draft and its evidence. It does not
                        restart services, provision databases or activate a
                        tenant.
                      </p>
                      <p>
                        Activation is a separate operational step and is not available from this workbench. Give the reviewed package to the engineer responsible for that procedure.
                      </p>
                      {draft.approval &&
                      draft.readiness.approve.ready &&
                      !dirty ? (
                        <div className="wb-success">
                          <strong>Approved for handoff</strong>
                          <details><summary>For engineers · artifact identity</summary><p>
                            Artifact digest:{" "}
                            <code>{draft.approval.digest}</code>
                          </p></details>
                        </div>
                      ) : (
                        <button
                          disabled={
                            dirty ||
                            busy ||
                            !!running ||
                            !draft.readiness.approve.ready
                          }
                          onClick={() => void perform(() => action("approve"))}
                        >
                          Approve this package
                        </button>
                      )}
                      <button
                        className="wb-secondary"
                        disabled={!pack || dirty || busy}
                        onClick={() =>
                          void perform(async () => {
                            setExported(
                              await request(`/tenants/${draft.id}/export`),
                            );
                          })
                        }
                      >
                        For engineers · preview pack and question files
                      </button>
                      {exported && (
                        <>
                          <h3>Pack YAML · generated, read-only</h3>
                          <pre>{exported.pack_yaml}</pre>
                          <h3>Evaluation YAML · same questions artifact</h3>
                          <pre>{exported.eval_yaml}</pre>
                          <button
                            className="wb-secondary"
                            onClick={() => {
                              const blob = new Blob([pretty(exported)], {
                                type: "application/json",
                              });
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement("a");
                              a.href = url;
                              a.download = `engram-${draft.id}-r${draft.revision}.json`;
                              a.click();
                              URL.revokeObjectURL(url);
                            }}
                          >
                            Download review package
                          </button>
                        </>
                      )}
                    </section>
                    <section className="wb-card">
                      <details>
                        <summary>
                          Revision history · {draft.history.length} entries
                        </summary>
                        {draft.history
                          .slice()
                          .reverse()
                          .map((h, i) => (
                            <p key={i}>
                              <strong>r{h.revision}</strong> ·{" "}
                              {h.action.split("_").join(" ")}
                              <br />
                              <small>
                                {h.operator} · {new Date(h.at).toLocaleString()}
                              </small>
                            </p>
                          ))}
                      </details>
                    </section>
                  </>
                )}
              </fieldset>
              <footer className="wb-flow-footer">
                <button
                  className="wb-secondary"
                  disabled={step === 0 || busy}
                  onClick={() =>
                    void go(step === 3 ? 2 : step === 4 ? 2 : Math.max(0, step - 1))
                  }
                >
                  <ArrowLeft size={16} /> Back
                </button>
                <span>
                  Step {step === 3 ? "3b" : step < 3 ? step + 1 : step} of 6 · Changes are
                  saved when you continue
                </span>
                <button
                  disabled={step === 6 || busy}
                  onClick={() =>
                    void go(
                      step === 2 || step === 3 ? 4 : Math.min(6, step + 1),
                    )
                  }
                >
                  {step === 6
                    ? "Complete"
                    : `Continue to ${steps[step === 2 || step === 3 ? 4 : step + 1]?.toLowerCase()}`}{" "}
                  <ArrowRight size={16} />
                </button>
              </footer>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function ObservedGraph({ step }: { step: any }) {
  if (!step) return null;
  const nodes = step.nodes.filter(
    (n: any) => !["Event", "OntologyState"].includes(n.type),
  );
  return (
    <>
      <p>
        {step.admitted ? "Event admitted" : `Event rejected: ${step.reason}`}.
        This view contains stored rows after this step.
      </p>
      <PackGraph nodes={nodes} edges={step.edges} mode="observed" />
      <div className="wb-model" aria-label="Observed domain nodes">
        {nodes.map((n: any) => (
          <article key={n.id}>
            <span className="wb-pill">{n.type}</span>
            <strong>{n.id}</strong>
            <dl>
              {Object.entries(n.properties)
                .filter(([k]) => !["embedding", "node_id"].includes(k))
                .slice(0, 8)
                .map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{typeof v === "object" ? pretty(v) : String(v)}</dd>
                  </div>
                ))}
            </dl>
          </article>
        ))}
      </div>
      <details>
        <summary>All stored nodes and relationships (accessible table)</summary>
        <div className="wb-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Node ID</th>
              </tr>
            </thead>
            <tbody>
              {step.nodes.map((n: any) => (
                <tr key={n.id}>
                  <td>{n.type}</td>
                  <td>{n.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Relationship</th>
                <th>Target</th>
              </tr>
            </thead>
            <tbody>
              {step.edges.map((e: any, i: number) => (
                <tr key={i}>
                  <td>{e.source}</td>
                  <td>{e.type}</td>
                  <td>{e.target}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}

function ListInput({
  values,
  onChange,
  placeholder,
}: {
  values: string[];
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
}) {
  const [text, setText] = useState(values.join(", "));
  const focused = useRef(false);
  const normalized = values.join(", ");
  useEffect(() => {
    if (!focused.current) setText(normalized);
  }, [normalized]);
  return (
    <input
      value={text}
      placeholder={placeholder}
      onFocus={() => {
        focused.current = true;
      }}
      onBlur={() => {
        focused.current = false;
        setText(normalized);
      }}
      onChange={(event) => {
        setText(event.target.value);
        onChange(event);
      }}
    />
  );
}

function MappingEvidence({ sample }: { sample: any }) {
  const [path, setPath] = useState<string>("");
  useEffect(() => {
    setPath("");
  }, [sample]);
  return (
    <div className="wb-mapping-evidence">
      <p className="wb-muted">
        Source record {sample.source_record || "unknown"} · Matching rules and
        planned effects come from the engine.
      </p>
      <div className="wb-grid">
        <section>
          <h3>Sample payload</h3>
          <pre>{pretty(sample.input)}</pre>
          <p className="wb-muted">
            Choose a top-level field to inspect its payload-relative path:
          </p>
          <div className="wb-inline">
            {Object.keys(sample.input || {})
              .filter((field) => /^[A-Za-z_][A-Za-z0-9_]*$/.test(field))
              .map((field) => (
                <button
                  className="wb-secondary"
                  key={field}
                  onClick={() => setPath(`$.${field}`)}
                >
                  {field}
                </button>
              ))}
          </div>
          {path && (
            <output className="wb-path" aria-live="polite">
              Expression: <code>{path}</code> · Sample value:{" "}
              {pretty(sample.input[path.slice(2)])}
            </output>
          )}
        </section>
        <section>
          <h3>Matching projection rule</h3>
          <pre>{pretty(sample.rules)}</pre>
        </section>
      </div>
      <details>
        <summary>Supported expression vocabulary</summary>
        <p className="wb-muted">
          Payload paths ($.field), event fields ($event.field), regex,
          regex_all, match, map, sha256 and each. Expressions are validated by
          the engine. Regex execution has a 0.25-second per-match limit; sample
          success does not establish worst-case timing.
        </p>
      </details>
    </div>
  );
}
