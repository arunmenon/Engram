"""Isolated shared-logic diagnostic, NOT Engram API/Spanner acceptance."""
import asyncio,json
from datetime import datetime,UTC
from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.composed_reads import ComposedReadView,ReadScope
from context_graph.settings import OntologySettings
from context_graph.ontology.runtime import configured_bundle
from context_graph.domain.models import EventNode
async def main():
 result={'scope':'Local isolated MemoryGraphStore diagnostics of shared GraphOperations; no HTTP, worker loops, LLM or Spanner execution. Direct writer calls below are diagnostic only and do not satisfy goal/pilot acceptance.'}
 graph=MemoryGraphStore()
 bundle=configured_bundle(OntologySettings(_env_file=None,packs=[],builtin_packs=['user']))
 await graph.write_user_profile({'user_id':'user:assessment-agent','display_name':'Assessment User'})
 view=ComposedReadView(graph,ReadScope.from_bundle(bundle))
 key=('UserProfile','profile:user:assessment-agent')
 raw=await graph.read_keyed_nodes([key]);scoped=await view.read_keyed_nodes([key]);user=await graph.get_user_profile('user:assessment-agent')
 result['profile_key_probe']={'raw_profile_present':key in raw,'specialized_user_read_present':user is not None,'composed_profile_present':key in scoped,'registry_key_field':view.scope.key_field('UserProfile'),'actual_stored_user_id':raw[key]['user_id'],'actual_stored_profile_id':raw[key]['profile_id'],'verdict':'local_reproduced_disagreement' if key in raw and key not in scoped else 'not_reproduced'}
 graph=MemoryGraphStore()
 data={'key':'answer_length','category':'style','polarity':'positive'}
 for _ in range(2):await graph.write_preference_with_edges('user:assessment-agent',data,[],{'method':'assessment_diagnostic'})
 random_count=len([k for k in graph.nodes if k[0]=='Preference'])
 graph=MemoryGraphStore()
 fixed={**data,'preference_id':'preference:assessment-fixed'}
 for _ in range(2):await graph.write_preference_with_edges('user:assessment-agent',fixed,[],{'method':'assessment_diagnostic'})
 props=(await graph.read_keyed_nodes([('Preference','preference:assessment-fixed')]))[('Preference','preference:assessment-fixed')]
 result['repeated_preference_writer_probe']={'without_supplied_id_two_calls_node_count':random_count,'with_fixed_id_two_calls_observation_count':props['observation_count'],'verdict':'writer_not_idempotent_for_repeated_identical_calls','limit':'Does not establish full worker retry/correction outcome; model/provider/consumer receipts were not exercised.'}
 graph=MemoryGraphStore()
 await graph.update_event_enrichment('assessment-event',['wanted-keyword'],8)
 await graph.merge_event_node(EventNode(event_id='assessment-event',event_type='tool.execute',occurred_at=datetime.now(UTC),session_id='s',agent_id='a',trace_id='t',global_position='assessment-only'))
 props=(await graph.read_keyed_nodes([('Event','assessment-event')]))[('Event','assessment-event')]
 result['enrichment_before_projection_probe']={'keywords_after_late_creation':props.get('keywords'),'expected_keyword_present':'wanted-keyword' in (props.get('keywords') or []),'verdict':'local_reproduced_lost_annotation','limit':'Shared adapter logic only. Full concurrent worker and Spanner convergence unverified.'}
 print(json.dumps(result,indent=2))
asyncio.run(main())
