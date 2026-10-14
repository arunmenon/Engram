"""Local schema/applicability check; no cloud, storage writes or acceptance claim."""
import asyncio
import json
from context_graph.domain.models import Event
from context_graph.domain.pack_admission import compile_admission_policy
from context_graph.domain.memory_actions import MemoryAction
from context_graph.domain.pack_extraction import extraction_profiles, parse_answer
from context_graph.ontology.runtime import configured_bundle
from engram_composition_assessment import settings_for
from engram_pack_combination_demo import CONFIGURATIONS, fixtures, DECISION, extraction, Providers, PackProvider
from engram_composition_reuse import TARGET
from context_graph.domain.extraction import SessionExtractionResult

for config in CONFIGURATIONS:
    plan = fixtures('combination-local', config)
    bundle = configured_bundle(settings_for('combination-local', config, target_database=TARGET.rsplit('/',1)[1]).ontology)
    policy = compile_admission_policy(bundle)
    for key, body in plan['events'].items():
        event = Event.model_validate(body, strict=False)
        allowed = policy.decide(event.event_type, body['payload']).allowed
        assert allowed == (key in plan['accepted']), (config, key, allowed)
        if allowed and event.event_type.startswith('memory.'):
            MemoryAction.from_event(event, body['payload'])
    for polarity in ['positive', 'negative']:
        SessionExtractionResult.model_validate(dict(session_id=plan['user_session'],agent_id='alice',**extraction(polarity)))
    profiles = extraction_profiles(bundle.registry, max_nodes=10, max_links=10, max_text_chars=10000)
    for profile in profiles:
        model = PackProvider(Providers(plan))
        text = plan['events']['preference']['payload']['content']
        raw = parse_answer(asyncio.run(model.generate_text(profile.prompt(text, []))))
        result = profile.plan(raw, Event.model_validate(plan['events']['preference'],strict=False), trusted=True, known=[])
        assert not result.rejected and result.accepted_nodes == 1, result.rejected
        assert result.plan.nodes[0].ref.key == plan['ids']['decision']
    print(config, 'packs', bundle.pack_identities, 'accepted', len(plan['accepted']), 'profiles', len(profiles))
print('ALL ENVELOPES, SELECTED CONTRACTS, MEMORY ACTIONS AND PROVIDER PROPOSALS VALID')
