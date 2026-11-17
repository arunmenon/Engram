/** Explain evidence without turning an expected HTTP status into an observed response. */
export function explainCheck(check: any, result: any): string {
  const e = result.expected || check?.expected || {};
  const a = result.actual || {};
  const step = check?.after_step == null ? "At the end of this story" : `After event ${check.after_step + 1}`;
  if (result.status === "unsupported") return `Not run here. ${result.explanation || e.reason || "This check has no supported executor in this environment."}`;
  if (result.status === "error") return "The check could not finish. This is not a passing result; inspect the technical details before retrying.";
  if (result.status === "passed") return "The observed result matched this check’s expected outcome.";
  switch (check?.kind) {
    case "disposition": {
      const expected = ({201: "accepted as new or duplicate", 409: "refused as a conflict", 422: "rejected"} as Record<number, string>)[e.http_status] || "handled as specified";
      return `${step}, Engram reported ${a.semantic_outcome || "no handling result"}; the story expected it to be ${expected}. This compares processing outcomes, not live HTTP responses.`;
    }
    case "node_present": return `${step}, ${e.node} should exist but was not found.`;
    case "node_absent": return `${step}, ${e.node} exists but should not.`;
    case "edge_present": return `${step}, the expected relationship is missing. Inspect the two entities and the relationship in the details.`;
    case "edge_absent": return `${step}, a relationship exists that the story forbids.`;
    case "properties": return `${step}, an entity is missing or its recorded fields differ from the expected values.`;
    case "property_absent": return `${step}, the entity is missing or still carries a field that should be absent.`;
    case "unchanged": return `${step}, the stored graph changed when the story expected it to stay unchanged.`;
    case "evidence_absent": return `${step}, an entity has evidence links that should not exist.`;
    case "edge_targets": return `${step}, the linked entities differ from the expected set.`;
    case "nodes_matching": return `${step}, the matching entities differ from the expected set.`;
    case "graph_exact": return `${step}, the graph differs in entities, fields, relationships or evidence. The details identify each difference.`;
    case "retrieval": return "The returned answer or its supporting evidence differs from the reviewed expectation. Check missing and unexpected answers in the details.";
    case "evaluation": return "The question evaluation did not meet the reviewed scoring or result requirements.";
    case "retrieval_benchmark": return "The comparison did not meet its expected per-question scores or work limits. Inspect the question results.";
    default: return "The observed result did not match this check. Inspect the expected and observed details; no diagnosis has been inferred.";
  }
}

/** Pick the next inspection step, not an inferred root cause or automatic repair. */
export function sandboxGuidance(result: any): {step: number; title: string; reason: string} {
  if (result.dead_letters?.length) return {
    step: 5, title: "Inspect event processing failures",
    reason: "Some events could not finish processing. Inspect their errors and handling before changing the pack or question expectations.",
  };
  if (result.missing_nodes?.length || result.forbidden_nodes?.length) return {
    step: 5, title: "Compare the stored graph with the expected graph",
    reason: "Entities are missing or unexpected. Inspect the event-by-event graph and mapping rules, then check the source material. An answer-type setting cannot repair the stored graph.",
  };
  return {
    step: 4, title: "Check the question setup and answer scope",
    reason: "First inspect the answer node type, selected starting entities, search mode and expected answers against the source material. Only the operator may correct an expectation, with a source-backed reason; never change it merely to pass a run. If these are correct, inspect retrieval and pack rules. A failed answer alone does not show that the pack needs rewriting.",
  };
}
