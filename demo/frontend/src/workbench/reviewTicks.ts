import type { Draft } from "./types";

export interface ReviewTicks {
  basis: string;
  changes: string[];
  removals: string[];
  policies: string[];
}

// Navigation does not change the basis; a different proposal/review or tenant does.
export function reviewTicksFor(draft: Draft, saved: ReviewTicks | null): ReviewTicks {
  const basis = JSON.stringify([draft.id, draft.proposal, draft.proposal_changes,
    draft.proposal_stale, draft.review]);
  if (saved?.basis === basis) return saved;
  return {basis, changes: draft.review?.accepted_changes || [],
    removals: draft.review?.accepted_removals || [], policies: draft.review?.confirmed_policies || []};
}
