import assert from "node:assert/strict";
import test from "node:test";
import {reviewTicksFor} from "../src/workbench/reviewTicks.ts";
import type {Draft} from "../src/workbench/types.ts";

const draft = {id:"tenant-a", revision:2, proposal:{pack:{types:{nodes:{Incident:{key:["id"]}}}}}, proposal_changes:[{id:"change-a"}], review:null, proposal_stale:false} as unknown as Draft;

test("review selections survive navigation/poll revisions, but not changed proposal or tenant", () => {
 const selected = {...reviewTicksFor(draft, null), changes:["change-a"], removals:["nodes.Incident.state"], policies:["identity"]};
 assert.deepEqual(reviewTicksFor({...draft, revision:3}, selected), selected);
 assert.deepEqual(reviewTicksFor({...draft,id:"tenant-b"},selected).changes,[]);
 assert.deepEqual(reviewTicksFor({...draft,proposal:{...draft.proposal!,summary:"Revised meaning"}},selected).policies,[]);
 assert.deepEqual(reviewTicksFor({...draft,proposal_stale:true},selected).removals,[]);
 assert.deepEqual(reviewTicksFor({...draft,proposal_changes:[{id:"different"}] as any},selected).changes,[]);
});

test("server review remains the baseline after explicit review updates", () => {
 const selected = {...reviewTicksFor(draft,null), policies:["identity"]};
 const reviewed = {...draft,review:{accepted_changes:["change-a"],accepted_removals:[],confirmed_policies:["identity","lifecycle"],accepted_facts:[]}} as Draft;
 assert.deepEqual(reviewTicksFor(reviewed,selected).policies,["identity","lifecycle"]);
});
