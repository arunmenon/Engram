"""Read-only local composition probe: no stores, models, credentials or cloud calls."""
import json,subprocess,logging,structlog
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))
from context_graph.settings import OntologySettings
from context_graph.ontology.runtime import configured_bundle
from context_graph.api.tenants import create_tenant_app,TenantServiceNotReadyError
cases=[('core',[],[]),('core+user',['user'],[]),('core+user+memory',['user','memory'],[]),('core+pdlc',[],['pdlc']),('core+pdlc+memory',['memory'],['pdlc'])]
result={'scope':'LOCAL configuration execution only; no live worker, API, model or Spanner acceptance','revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'configurations':[]}
for name,builtins,domains in cases:
 bundle=configured_bundle(OntologySettings(_env_file=None,builtin_packs=builtins,packs=domains))
 registry=bundle.registry
 profiles=[]
 for pack in registry.packs:
  ex=pack.extraction
  if ex and ex.sources and ex.propose:profiles.append({'pack':pack.name,'sources':list(ex.sources),'propose':sorted(ex.propose)})
 result['configurations'].append({'name':name,'settings':{'builtin_packs':builtins,'packs':domains},'packs':list(bundle.pack_identities),'bundle_identity':bundle.identity,'schema_version':bundle.schema_version,'processing':list(bundle.processing),'nodes':sorted(bundle.node_types),'edges':sorted(bundle.edge_types),'intents':sorted(bundle.declared_intents),'projection_rule_counts':{pack.name:len(pack.projection) for pack in registry.packs},'extraction_profiles':profiles,'user_enabled':bundle.enables('user.extract.v1')})
try:create_tenant_app(None)
except TenantServiceNotReadyError as e:result['public_tenant_factory']={'observed':'fail_closed','error':str(e),'scope':'local factory invocation, no stores opened'}
by={c['name']:c for c in result['configurations']}
result['matched_comparisons']={
 'user_vs_user_memory_same_handlers':by['core+user']['processing']==by['core+user+memory']['processing'],
 'pdlc_vs_pdlc_memory_same_handlers':by['core+pdlc']['processing']==by['core+pdlc+memory']['processing'],
 'all_core_mandatory':all(any(p[0]=='core' for p in c['packs']) for c in result['configurations']),
 'no_user_handler_without_user':all(c['user_enabled']==any(p[0]=='user' for p in c['packs']) for c in result['configurations'])}
print(json.dumps(result,indent=2))
