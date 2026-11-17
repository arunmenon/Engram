import type { Draft } from "./types";

export interface PreparedRequest {
  itemKey: string;
  subject: string;
  answer: string;
  reviewedRevision: number | null;
  proposal: string;
}

/** Human text outlives a revision; an agent explanation must not. */
export const answerKey = (draftId: string, scope: string, subject: string) =>
  JSON.stringify([draftId, scope, subject]);

export function requestNeedsReview(request: PreparedRequest, draft: Pick<Draft, "revision" | "proposal">, answer: string) {
  return request.reviewedRevision !== draft.revision ||
    request.proposal !== JSON.stringify(draft.proposal) || request.answer !== answer;
}

/** Candidates come from declared names, not a fabricated semantic effect. */
export function affectedRules(pack: any, subject: string, text: string) {
  const words = `${subject} ${text}`.toLowerCase();
  const mentioned = (name: string) => new RegExp(`(^|[^a-z0-9_])${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").toLowerCase()}([^a-z0-9_]|$)`).test(words);
  return Object.entries<any>(pack?.types?.nodes || {}).filter(([name]) => mentioned(name)).slice(0, 8).map(([name, type]) => ({
    name,
    identity: (type.key || []).join(" + "),
    states: (type.lifecycle?.states || []).join(", "),
    events: (pack?.projection || []).filter((rule: any) => (rule.upsert || []).some((write: any) => write.type === name)).map((rule: any) => rule.event),
  }));
}
