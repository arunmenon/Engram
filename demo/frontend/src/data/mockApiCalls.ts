export interface ApiCall {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  endpoint: string;
  latency_ms: number;
  status: number;
  timestamp: string;
  request?: Record<string, unknown>;
  response?: Record<string, unknown>;
}

export const mockApiCalls: ApiCall[] = [
  {
    id: 'api-1',
    method: 'POST',
    endpoint: '/v1/events',
    latency_ms: 12,
    status: 201,
    timestamp: '2024-03-22T09:00:01Z',
    request: {
      event_type: 'observation.input',
      session_id: 'session-3',
      agent_id: 'support-agent-1',
      payload_ref: 'evt:evt-3-1',
      importance_hint: 10,
    },
    response: {
      event_id: 'evt-3-1',
      global_position: '1711094401000-0',
      status: 'accepted',
    },
  },
  {
    id: 'api-2',
    method: 'POST',
    endpoint: '/v1/query/subgraph',
    latency_ms: 145,
    status: 200,
    timestamp: '2024-03-22T09:00:02Z',
    request: {
      query: 'Kanban board data loss',
      session_id: 'session-3',
      user_id: 'entity-sarah',
      max_nodes: 100,
      max_depth: 3,
    },
    response: {
      nodes_returned: 18,
      truncated: false,
      inferred_intents: { why: 0.9, what: 0.7 },
      query_ms: 145,
    },
  },
  {
    id: 'api-3',
    method: 'GET',
    endpoint: '/v1/users/sarah/preferences',
    latency_ms: 23,
    status: 200,
    timestamp: '2024-03-22T09:00:03Z',
    response: {
      preferences: [
        { category: 'communication', value: 'email', polarity: 'positive', confidence: 0.95 },
        { category: 'workflow', value: 'kanban', polarity: 'positive', confidence: 0.85 },
      ],
    },
  },
  {
    id: 'api-4',
    method: 'GET',
    endpoint: '/v1/users/sarah/profile',
    latency_ms: 18,
    status: 200,
    timestamp: '2024-03-22T09:00:03Z',
    response: {
      name: 'Sarah Chen',
      role: 'Engineering Team Lead',
      tech_level: 'advanced',
      session_count: 3,
    },
  },
  {
    id: 'api-5',
    method: 'POST',
    endpoint: '/v1/events',
    latency_ms: 8,
    status: 201,
    timestamp: '2024-03-22T09:02:01Z',
    request: {
      event_type: 'tool.execute',
      tool_name: 'escalate_ticket',
      session_id: 'session-3',
      parent_event_id: 'evt-3-1',
    },
    response: {
      event_id: 'evt-3-2',
      global_position: '1711094521000-0',
    },
  },
  {
    id: 'api-6',
    method: 'GET',
    endpoint: '/v1/lineage/evt-3-1?direction=backward&max_depth=3',
    latency_ms: 67,
    status: 200,
    timestamp: '2024-03-22T09:02:05Z',
    response: {
      root: 'evt-3-1',
      paths: [
        ['evt-3-1', 'entity-kanban', 'evt-2-3', 'entity-swimlanes'],
        ['evt-3-1', 'entity-sprint-data'],
      ],
      nodes_traversed: 8,
    },
  },
  {
    id: 'api-7',
    method: 'POST',
    endpoint: '/v1/query/subgraph',
    latency_ms: 198,
    status: 200,
    timestamp: '2024-03-22T09:08:01Z',
    request: {
      query: 'data recovery status',
      session_id: 'session-3',
      user_id: 'entity-sarah',
      scoring_weights: { recency: 1.5, importance: 2.0, relevance: 1.0 },
    },
    response: {
      nodes_returned: 24,
      proactive_nodes_count: 5,
      inferred_intents: { why: 0.7, what: 0.8, related: 0.4 },
      query_ms: 198,
    },
  },
];
