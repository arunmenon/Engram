"""Read-only local probes of the pinned dev snapshot; no services or model calls."""
import asyncio
import json
from datetime import datetime, UTC
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

from context_graph.api.dependencies import require_api_key, require_tenant
from context_graph.domain.models import Event, Edge, EdgeType, NodeType
from context_graph.domain.pagination import encode_cursor, decode_cursor
from context_graph.adapters.llm.client import LLMExtractionClient

async def main():
    settings = SimpleNamespace(
        auth=SimpleNamespace(api_key='dummy-review-key'),
        tenant=SimpleNamespace(enabled=True, header_name='X-Tenant-ID', id_pattern=r'^[a-z0-9-]+$'),
    )
    tenants=[]
    for tenant in ('tenant-a','tenant-b'):
        request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)), headers={'authorization':'Bearer dummy-review-key','X-Tenant-ID':tenant})
        await require_api_key(request)
        tenants.append((await require_tenant(request)).tenant_id)
    cursor=encode_cursor('2026-01-01T00:00:00Z','event-1')
    edge=Edge(source='arbitrary-source',target='arbitrary-target',edge_type=EdgeType.REFERENCES,properties={'role':'not-a-valid-role'})
    client=LLMExtractionClient(max_retries=0)
    client._call_llm=AsyncMock(side_effect=RuntimeError('simulated model unavailable'))
    event=Event(event_id=uuid4(),event_type='observation.input',occurred_at=datetime.now(UTC),session_id='review-session',agent_id='review-agent',trace_id='review-trace',payload_ref='review-payload')
    result=await client.extract_from_session([event],'review-session','review-agent')
    print(json.dumps({
        'node_types':len(NodeType),'edge_types':len(EdgeType),
        'same_api_key_accepted_tenant_headers':tenants,
        'unsigned_cursor_roundtrip':decode_cursor(cursor),
        'generic_edge_accepts_invalid_role':edge.properties['role'],
        'model_failure_returned_without_exception':True,
        'model_failure_result':result,
        'limitations':'Local function/model probes only; no Redis, Neo4j, HTTP deployment, or external model services.'
    },indent=2,default=str))

asyncio.run(main())
