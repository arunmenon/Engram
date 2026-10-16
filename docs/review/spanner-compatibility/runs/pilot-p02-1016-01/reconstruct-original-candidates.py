import asyncio,json
from pathlib import Path
from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.adapters.memory.subscription import MemorySubscription
from context_graph.domain.models import Event
from context_graph.domain.pack_extraction import extraction_profiles,event_text
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology import load_registry
from context_graph.settings import Settings
from context_graph.worker.pack_extraction import PackExtractionConsumer,search_terms
from context_graph.worker.pack_projection import apply_plan
async def main():
 p=Path('docs/review/spanner-compatibility/runs/pilot-p02-1016-01');before=json.loads((p/'b-before.json').read_text())['snapshot'];g=MemoryGraphStore()
 g.nodes={(r[0],r[1]):r[2] for r in before['nodes']}
 registry=load_registry(['pdlc']);projector=PackProjector(registry,frozenset({'completion.publisher'}));profile=extraction_profiles(registry,max_nodes=20,max_links=40,max_text_chars=20000)[0]
 plan=json.loads((p/'fixtures.json').read_text())['spectrum']['groups'][0]
 for i,s in enumerate(plan['steps']):
  e=Event.model_validate_json(json.dumps(s['request'])).model_copy(update={'global_position':str(i+1)+'-0'})
  await apply_plan(g,projector.plan(e,s['request']),1000)
  if s['scenario']=='H09-proposed-coverage':break
 log=MemoryEventLog();consumer=PackExtractionConsumer(MemorySubscription(log.stream,'diagnostic','one'),log,g,[profile],projector,None,Settings())
 text=event_text(s['request'],20000);known=await consumer._known_items(profile,e,s['request'],text)
 out={'classification':'Local deterministic reconstruction from saved before snapshot and accepted frozen projection inputs, not captured live prompt and not acceptance proof','terms':search_terms(text,12),'known':[{'id':k.node_id,'type':k.node_type,'label':k.label} for k in known],'expected_endpoints':plan['ids']}
 (p/'candidate-reconstruction.json').write_text(json.dumps(out,indent=2)+'\n');print('candidate_count',len(known));print(json.dumps(out['known'],indent=2));print('expected',plan['ids']['planned_case'],plan['ids']['proposed'])
import ast,subprocess
import context_graph.worker.pack_extraction as module
source=subprocess.check_output(['git','show','f500f8a:src/context_graph/worker/pack_extraction.py'],text=True)
tree=ast.parse(source)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PackExtractionConsumer')
method=next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='_known_items')
namespace=dict(module.__dict__)
unit=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),method],type_ignores=[])
exec(compile(ast.fix_missing_locations(unit),'recorded-candidate-method','exec'),namespace)
PackExtractionConsumer._known_items=namespace['_known_items']
asyncio.run(main())
