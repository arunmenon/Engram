import test from "node:test";
import assert from "node:assert/strict";
import { suggestCategory } from "../src/workbench/intake.ts";

test("intake suggestions recognize mixed materials without inventing a schema", () => {
  assert.equal(suggestCategory("Orders need finance approval before payment.").kind, "specification");
  assert.equal(suggestCategory(JSON.stringify({type: "object", properties: {order_id: {type: "string"}}})).kind, "schema");
  for (const event_type of ["crm.contact.updated", "purchase.approved"]) {
    assert.equal(suggestCategory(JSON.stringify([{event_type, payload: {id: "42"}}])).kind, "samples");
  }
  assert.equal(suggestCategory('{"meaning":"unknown"}').kind, null);
  assert.equal(suggestCategory('[]').kind, null);
  assert.equal(suggestCategory('{"event_type":"x", "payload":[]}').kind, null);
  assert.equal(suggestCategory('null').kind, null);
});
