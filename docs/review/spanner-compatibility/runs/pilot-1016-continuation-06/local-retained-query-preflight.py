import asyncio,json
from pathlib import Path
from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.spanner.log import json_value
from context_graph.ontology import load_registry
from context_graph.ports.pack_graph import NodeRef,NodeWrite,EdgeWrite
from context_graph.retrieval.artifacts import ArtifactQuery,ArtifactRetriever
from engram_goal03_implementation_demo import assert_retrieval_policy
from engram_pilot_spectrum import discovery_eligibility

async def main():
 p=Path('docs/review/spanner-compatibility/runs/pilot-1016-continuation-06')
 state=json.loads((p/'b-final-state.json').read_text())['snapshot']
 group=json.loads(Path('docs/pilot/pilot-p01-1016-07-journeys.json').read_text())['groups'][1]
 graph=MemoryGraphStore();reg=load_registry(['pdlc'])
 await graph.upsert_nodes([NodeWrite(NodeRef(r[0],r[1]),json_value(r[2])) for r in state['nodes']])
 await graph.upsert_edges([EdgeWrite(r[2],NodeRef(r[0],r[1]),NodeRef(r[3],r[4]),json_value(r[5])) for r in state['edges']])
 retriever=ArtifactRetriever(graph,reg,default_max_depth=6,seed_limit=10,neighbor_limit=200,provenance_source='memory')
 rows=[]
 for q in group['queries']:
  answer=(await retriever.retrieve(ArtifactQuery(q['text'],seed_node_ids=tuple(q.get('seeds') or [q['seed']] if q.get('seed') else q.get('seeds') or []),intent=q['intent'],max_depth=q['max_depth']))).model_dump(mode='json')
  actual=set(answer['nodes']);required=set(q['required']);extra=actual-required
  errors=[]
  if not required<=actual:errors.append('missing:'+str(sorted(required-actual)))
  if set(q['forbidden'])&actual:errors.append('forbidden:'+str(sorted(set(q['forbidden'])&actual)))
  if q.get('exact') and extra:errors.append('extra:'+str(sorted(extra)))
  if answer['meta'].get('truncated'):errors.append('truncated')
  if q.get('global_discovery'):
   _,eligible=discovery_eligibility(state,q['global_discovery'],q['max_depth'])
   if not actual<=eligible:errors.append('irrelevant:'+str(sorted(actual-eligible)))
   for kind,count in q.get('minimum_types',{}).items():
    if sum(n.startswith(kind+':') for n in actual)<count:errors.append('missing-type:'+kind)
  try:assert_retrieval_policy(answer,q)
  except AssertionError as e:errors.append(str(e))
  rows.append(dict(scenario=q['scenario'],nodes=len(actual),errors=errors))
 out=Path('/private/tmp/p01-retained-local-preflight.json');out.write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps(rows,indent=2))
asyncio.run(main())
