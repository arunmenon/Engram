import assert from "node:assert/strict";
import test from "node:test";
import { sampleEntities } from "../src/workbench/entityOptions.ts";
import type { Draft } from "../src/workbench/types.ts";

test("names, job titles and identifiers remain searchable without changing selection IDs", () => {
  const draft = {proposal:{pack:{types:{nodes:{Contact:{key:["account_id","contact_id"]}}}}}, validation:{samples:[{planned:{nodes:[
    {ref:{label:"Contact",key:"Contact:a|C2"},properties:{account_id:"a",contact_id:"C2",name:"Bo",title:"Buyer"}},
    {ref:{label:"Contact",key:"Contact:b|C2"},properties:{account_id:"b",contact_id:"C2",name:"Bo",title:"Director"}},
  ]}}]}} as unknown as Draft;
  const options = sampleEntities(draft);
  assert.equal(options.length,2);
  assert.equal(options[0].id,"Contact:a|C2");
  assert.match(options[0].label,/Bo/);
  assert.notEqual(options[0].label,options[1].label);
  for (const query of ["bo","buyer","c2","a"]) assert.ok(options[0].searchText!.toLowerCase().includes(query));
});

test("delivery titles and unnamed entities work with the same label derivation", () => {
 const draft={proposal:{pack:{types:{nodes:{Change:{key:["repo","number"]}}}}},validation:{samples:[{planned:{nodes:[
  {ref:{label:"Change",key:"Change:r|1"},properties:{repo:"r",number:1,title:"Repair checkout"}},
  {ref:{label:"Change",key:"Change:r|2"},properties:{repo:"r",number:2}},
 ]}}]}} as unknown as Draft;
 const options=sampleEntities(draft);
 assert.match(options[0].label,/Repair checkout/);assert.match(options[1].label,/r \/ 2/);
});
