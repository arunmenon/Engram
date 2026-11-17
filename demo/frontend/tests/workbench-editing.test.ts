import assert from "node:assert/strict";
import test from "node:test";
import { preserveEdits, changedFields, recoveryKey, readRecovery, resumeKey, readResumeStep } from "../src/workbench/editing.ts";
import { initialContent } from "../src/workbench/types.ts";

test("resume metadata is operator/customer scoped and never restores an invalid step", () => {
  assert.notEqual(resumeKey("alice", "one"), resumeKey("bob", "one"));
  assert.notEqual(resumeKey("alice", "one"), resumeKey("alice", "two"));
  for (const value of [null, "", "7", "-1", "NaN", "2.5", "2junk"]) assert.equal(readResumeStep(value), 0);
  assert.equal(readResumeStep("5"), 5);
});

test("a late save or poll preserves newer typed answers and server-only updates", () => {
  const base = initialContent("Customer", "dev");
  const local = { ...base, scope: "Still typing", decisions: { identity: "account + id" } };
  const incoming = { ...base, environment: "review" };
  assert.deepEqual(preserveEdits(base, local, incoming), { ...local, environment: "review" });
  assert.deepEqual(changedFields(base, incoming), ["environment"]);
  assert.deepEqual(preserveEdits(local, local, incoming), incoming);
});

test("recovery is scoped, bounded in time, and rejects malformed data", () => {
  assert.notEqual(recoveryKey("alice", "one"), recoveryKey("bob", "one"));
  assert.notEqual(recoveryKey("alice", "one"), recoveryKey("alice", "two"));
  const r = {savedAt: 1000, revision: 1, content: initialContent("C", "dev"),
    step: 2, sourceName: "", sourceText: "unfinished", sourceKind: "samples", authorPrompt: "keep this"};
  assert.deepEqual(readRecovery(JSON.stringify(r), 1100), r);
  assert.equal(readRecovery(JSON.stringify(r), 86401001), null);
  assert.equal(readRecovery("{bad", 1100), null);
});

test("adding a source retains the submitted addition as well as text typed during its save", () => {
  const beforeRequest = initialContent("Customer", "dev");
  const submitted = {...beforeRequest, sources: [{id:"s1", name:"Runbook", kind:"specification" as const, text:"Example"}]};
  const whileSaving = {...beforeRequest, scope:"A new scope typed while saving"};
  const result = preserveEdits(beforeRequest, whileSaving, submitted);
  assert.deepEqual(result.sources, submitted.sources);
  assert.equal(result.scope, whileSaving.scope);
});
