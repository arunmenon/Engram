import test from "node:test";
import assert from "node:assert/strict";
import { explainCheck } from "../src/workbench/results.ts";

test("conflicting retry explanation does not claim an observed HTTP response", () => {
  const text = explainCheck({kind:"disposition", after_step:18}, {
    status:"failed", expected:{http_status:409}, actual:{semantic_outcome:"duplicate"},
  });
  assert.match(text, /event 19/);
  assert.match(text, /reported duplicate/);
  assert.match(text, /refused as a conflict/);
  assert.match(text, /not live HTTP/);
});
test("unsupported reason and execution errors remain distinct from passing results", () => {
  assert.match(explainCheck({}, {status:"unsupported", explanation:"Needs a larger fixture"}), /Needs a larger fixture/);
  assert.doesNotMatch(explainCheck({}, {status:"unsupported"}), /deployed/);
  assert.match(explainCheck({}, {status:"error"}), /not a passing result/);
});

import { sandboxGuidance } from "../src/workbench/results.ts";

test("answer-only failure leads to question settings, not an assumed engine correction", () => {
  const result = {passed: false, missing_nodes: [], forbidden_nodes: [], dead_letters: [],
    evaluation: {mean_f1: 0.667}};
  assert.equal(sandboxGuidance(result).step, 4);
  assert.match(sandboxGuidance(result).reason, /answer node type/);
  assert.equal(sandboxGuidance({...result, missing_nodes: ["Incident:x"]}).step, 5);
  assert.match(sandboxGuidance({...result, dead_letters: [{}]}).title, /processing/);
});
