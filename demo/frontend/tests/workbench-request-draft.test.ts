import assert from "node:assert/strict";
import test from "node:test";
import { answerKey, requestNeedsReview, affectedRules } from "../src/workbench/requestDraft.ts";
import { readRecovery } from "../src/workbench/editing.ts";
import { initialContent } from "../src/workbench/types.ts";

test("human answer identity is independent of revision but scoped to draft and subject", () => {
  const key = answerKey("one", "limitation", "Which attempt counts?");
  assert.equal(key, answerKey("one", "limitation", "Which attempt counts?"));
  assert.notEqual(key, answerKey("two", "limitation", "Which attempt counts?"));
  assert.notEqual(key, answerKey("one", "limitation", "Which invoice counts?"));
});

test("saved, changed, and restored requests need explicit review against current context", () => {
  const draft = {revision: 2, proposal: null};
  const request = {itemKey:"one", subject:"Policy", answer:"Keep history", reviewedRevision:2, proposal:"null"};
  assert.equal(requestNeedsReview(request, draft, "Keep history"), false);
  assert.equal(requestNeedsReview(request, {...draft, revision:3}, "Keep history"), true);
  assert.equal(requestNeedsReview({...request, reviewedRevision:null}, draft, "Keep history"), true);
  assert.equal(requestNeedsReview(request, draft, "Delete history"), true);
});

test("recovery carries human answers and request origin together, never an agent answer", () => {
  const state = {savedAt:1000, revision:2, content:initialContent("Tenant","test"), step:2,
    sourceName:"", sourceText:"", sourceKind:"specification", authorPrompt:"Keep history",
    operatorAnswers:{one:"Keep history"}, preparedRequest:{itemKey:"one",subject:"Contact identity",answer:"Keep history",reviewedRevision:2,proposal:"null"}};
  assert.deepEqual(readRecovery(JSON.stringify(state),1100),state);
  assert.equal(readRecovery(JSON.stringify({...state,operatorAnswers:{one:42}}),1100),null);
});

test("scope preview exposes declared rules without inventing a readiness relationship", () => {
  const pack = {types:{nodes:{Contact:{key:["email"]}, TestRun:{key:["run_id"]}}}, projection:[{event:"contact.changed",upsert:[{type:"Contact"}]}]};
  const preview = affectedRules(pack,"Contact changes email", "Keep the same person");
  assert.deepEqual(preview,[{name:"Contact",identity:"email",states:"",events:["contact.changed"]}]);
  assert.deepEqual(affectedRules(pack,"Unspecified readiness rule", "What should happen?"),[]);
});
