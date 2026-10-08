"""Local-only schema/configuration probe; no stores, credentials or cloud calls."""
import json
import logging
import structlog
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))
from context_graph.ontology.loader import load_registry, load_pack_file, BUILTIN_PACK_DIR
from context_graph.domain.ontology import OntologyRegistry
from context_graph.settings import OntologySettings
from context_graph.ontology.runtime import configured_registry
packs={n:load_pack_file(BUILTIN_PACK_DIR/f'{n}.pack.yaml') for n in ('core','memory','user','pdlc')}
def check(fn):
    try:
        r=fn()
        return {'packs':[p.name for p in r.packs], 'nodes':len(r.node_types), 'accepts_pdlc_unknown':r.accepts_event_type('pdlc.unknown'), 'accepts_unknown_domain':r.accepts_event_type('unknown.created')}
    except Exception as e:
        return {'error':str(e)[:700]}
result={'scope':'LOCAL ONLY: configuration and schema composition; no worker/store/runtime or cloud acceptance'}
result['loader']={str(ns):check(lambda ns=ns:load_registry(ns)) for ns in ([],['core','pdlc'],['core','memory'],['core','user'],['memory','user','pdlc'],['does_not_exist'])}
result['default']=check(lambda:configured_registry(OntologySettings(_env_file=None)))
result['schema_only']={'+'.join(ns):check(lambda ns=ns:OntologyRegistry([packs[n] for n in ns])) for ns in (['core'],['core','pdlc'],['core','memory'],['core','user'],['core','memory','user','pdlc'],['pdlc'],['memory'],['user'])}
bad=packs['pdlc'].model_copy(update={'pack':packs['pdlc'].pack.model_copy(update={'requires':['core>=99.0']})})
result['invalid_version']=check(lambda:OntologyRegistry([packs['core'],bad]))
result['two_configuration_objects']=[check(lambda ns=ns:configured_registry(OntologySettings(packs=ns,_env_file=None))) for ns in ([],['pdlc'])]
result['two_configuration_objects_note']='Distinct cached configuration objects are possible. No tenant-to-registry/store routing follows from this.'
print(json.dumps(result,indent=2))
