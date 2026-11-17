import asyncio, json
from datetime import UTC, datetime, timedelta
from uuid import UUID
from pathlib import Path
from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import Event
from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology import load_registry
from context_graph.ports.pack_graph import NodeRef
from context_graph.worker.pack_projection import apply_plan

ROOT = Path('docs/review/spanner-compatibility/runs/20261007-local-update-semantics-probe-01')
core = load_registry([], builtin_packs=[]).pack('core')
lab = Pack.model_validate({
 'pack': {'name':'lab','version':'0.1.0','requires':['core>=1.1']},
 'types': {'nodes': {'Sample': {'key':['facility','sample_id'],
    'properties': {'facility':'string','sample_id':'string','description':'string','reading':'int'}}}},
 'events': {'lab.sample.updated': {}},
 'projection': [{'event':'lab.sample.updated','upsert':[{'type':'Sample',
    'key':{'facility':'$.facility','sample_id':'$.sample_id'},
    'set':{'description':'$.description','reading':'$.reading'}}]}]})
registry = OntologyRegistry([core,lab])
projector = PackProjector(registry,frozenset())
ref = NodeRef('Sample','Sample:west|S-7')
async def case(payloads):
 graph = MemoryGraphStore(); output=[]
 for i,payload in payloads:
  event = Event(event_id=UUID(int=i),event_type='lab.sample.updated',
   occurred_at=datetime(2026,10,7,tzinfo=UTC)+timedelta(minutes=i),
   session_id='probe',agent_id='fixture',trace_id='probe',payload_ref='fixture',
   global_position=f'{i}-0')
  plan = projector.plan(event,{'payload':{'facility':'west','sample_id':'S-7',**payload}})
  await apply_plan(graph,plan,100)
  output.append({'event':i,'planned_properties':plan.nodes[0].properties,
    'stored':(await graph.get_nodes([ref]))[ref]})
 return output
async def main():
 a={'description':'old','reading':1};b={'description':'new','reading':2}
 cases = {
  'omitted': await case([(1,a),(2,{})]),
  'explicit_null': await case([(1,a),(2,{'description':None,'reading':None})]),
  'invalid_coercion': await case([(1,a),(2,{'reading':'not-an-integer'})]),
  'retry_A_B_A': await case([(1,a),(2,b),(1,a)]),
 }
 assert cases['omitted'][-1]['stored']['description']=='old'
 assert cases['explicit_null'][-1]['stored']['description']=='old'
 assert cases['invalid_coercion'][-1]['stored']['reading']==1
 assert cases['retry_A_B_A'][-1]['stored']['description']=='old'
 (ROOT/'probe-evidence.json').write_text(json.dumps(cases,indent=2))
 print('4 diagnostic cases reproduced; omission/null preserve, invalid coercion silent no-op, A/B/A restores old value. No cloud/admission claims.')
asyncio.run(main())
