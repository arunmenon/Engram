import type { ReviewTicks } from "./reviewTicks";
import type { PreparedRequest } from "./requestDraft";
import type { Content } from "./types";

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/** Keep edits made after a request began; the server owns unchanged fields. */
export function preserveEdits(base: Content, local: Content, incoming: Content): Content {
  const result = { ...incoming };
  for (const key of Object.keys(local) as (keyof Content)[]) {
    if (!same(local[key], base[key])) Object.assign(result, { [key]: local[key] });
  }
  return result;
}

export function changedFields(base: Content, incoming: Content): string[] {
  return (Object.keys(base) as (keyof Content)[]).filter(k => !same(base[k], incoming[k]));
}

export const recoveryKey = (operator: string, id: string) =>
  `engram-edit:${encodeURIComponent(operator)}:${id}`;

export const resumeKey = (operator: string, id: string) =>
  `engram-step:${encodeURIComponent(operator)}:${id}`;

/** Only navigation metadata persists across tabs; draft inputs remain session-scoped. */
export function readResumeStep(raw: string | null): number {
  if (raw === null || !/^[0-6]$/.test(raw)) return 0;
  return Number(raw);
}

export interface Recovery {
  savedAt: number;
  revision: number;
  content: Content;
  step: number;
  sourceName: string;
  sourceText: string;
  sourceKind: "specification" | "schema" | "samples";
  authorPrompt: string;
  operatorAnswers?: Record<string, string>;
  preparedRequest?: PreparedRequest | null;
  reviewTicks?: ReviewTicks | null;
}

export function readRecovery(raw: string | null, now = Date.now()): Recovery | null {
  try {
    const r = JSON.parse(raw || "null");
    if (!r || now - r.savedAt > 24 * 60 * 60 * 1000 || r.savedAt > now ||
        !Number.isFinite(r.savedAt) || !Number.isInteger(r.revision) ||
        !r.content || typeof r.content.scope !== "string" ||
        !Number.isInteger(r.step) || r.step < 0 || r.step > 6 ||
        typeof r.sourceText !== "string" || typeof r.authorPrompt !== "string") return null;
    if (r.operatorAnswers !== undefined && (!r.operatorAnswers || typeof r.operatorAnswers !== "object" || Array.isArray(r.operatorAnswers) ||
        Object.values(r.operatorAnswers).some(v => typeof v !== "string"))) return null;
    if (r.preparedRequest != null && (typeof r.preparedRequest.itemKey !== "string" || typeof r.preparedRequest.subject !== "string" ||
        typeof r.preparedRequest.answer !== "string" || typeof r.preparedRequest.proposal !== "string" ||
        (r.preparedRequest.reviewedRevision !== null && !Number.isInteger(r.preparedRequest.reviewedRevision)))) return null;
    if (r.reviewTicks != null && (typeof r.reviewTicks.basis !== "string" ||
      [r.reviewTicks.changes, r.reviewTicks.removals, r.reviewTicks.policies].some(values =>
        !Array.isArray(values) || values.some((value: unknown) => typeof value !== "string")))) return null;
    return r;
  } catch { return null; }
}
