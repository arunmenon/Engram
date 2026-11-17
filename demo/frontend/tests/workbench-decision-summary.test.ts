import test from "node:test";
import assert from "node:assert/strict";
import { relationshipChanges, lifecycleComparison, decisionEvidence } from "../src/workbench/decisionSummary.ts";

test("relationship changes retain named changes, including equal totals with changed endpoints", () => {
  const result = relationshipChanges([["a", "WORKS_AT", "x"]], [["b", "WORKS_AT", "x"]]);
  assert.deepEqual(result, [{name: "works at", before: 1, after: 1, added: 1, removed: 1}]);
  assert.deepEqual(relationshipChanges([], []), []);
});

test("lifecycle comparison names current rules and does not infer executed starting states", () => {
  const base = {sample: 3, event: "case.resolved", record: "east42", to: "resolved", only_from: ["open"]};
  const next = {...base, only_from: ["open", "resolved"]};
  const result = lifecycleComparison([base], [next], "open")[0];
  assert.deepEqual(result.current?.only_from, ["open"]);
  assert.deepEqual(result.unrepresented, ["resolved"]);
  // An earlier request or initial state is visible evidence, not proof of guard acceptance.
  assert.deepEqual(lifecycleComparison([base], [{...next, sample: 1}, next], "open")[1].unrepresented, []);
  assert.deepEqual(lifecycleComparison([base], [next], "resolved")[0].unrepresented, []);
  assert.deepEqual(lifecycleComparison([base], [base], "open")[0].unrepresented, []);
});

test("decision evidence uses question and effect, with honest legacy fallback", () => {
  assert.equal(decisionEvidence('{"question":"One history?","effect":"Email changes."}'), "One history? Email changes.");
  assert.equal(decisionEvidence("Legacy question"), "Legacy question");
});
