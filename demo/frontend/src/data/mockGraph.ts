import type { GraphNode, GraphEdge } from '../types/graph';

// Deterministic position jitter using a seeded PRNG
let seed = 42;
function seededRandom() {
  seed = (seed * 16807 + 0) % 2147483647;
  return (seed - 1) / 2147483646;
}
const pos = (x: number, y: number) => ({
  x: x + (seededRandom() - 0.5) * 50,
  y: y + (seededRandom() - 0.5) * 50,
});

export const mockNodes: GraphNode[] = [
  // === SESSION 1 EVENTS ===
  { id: 'evt-1-start', label: 'Session Start', node_type: 'Event', session_id: 'session-1', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 0), attributes: { event_type: 'system.session_start' }, decay_score: 0.42, importance: 3 },
  { id: 'evt-1-1', label: 'User: Billing Issue', node_type: 'Event', session_id: 'session-1', event_type: 'observation.input', color: '#f59e0b', size: 6, ...pos(50, 0), attributes: { event_type: 'observation.input', content: 'Charged twice for Nimbus Pro' }, decay_score: 0.45, importance: 7 },
  { id: 'evt-1-2', label: 'Billing Lookup', node_type: 'Event', session_id: 'session-1', event_type: 'tool.execute', color: '#22c55e', size: 5, ...pos(100, 20), attributes: { event_type: 'tool.execute', tool_name: 'billing_lookup' }, decay_score: 0.43, importance: 5 },
  { id: 'evt-1-3', label: 'Agent: Found Error', node_type: 'Event', session_id: 'session-1', event_type: 'agent.invoke', color: '#3b82f6', size: 6, ...pos(150, 0), attributes: { event_type: 'agent.invoke' }, decay_score: 0.44, importance: 6 },
  { id: 'evt-1-4', label: 'Refund Initiated', node_type: 'Event', session_id: 'session-1', event_type: 'tool.execute', color: '#22c55e', size: 6, ...pos(200, 20), attributes: { event_type: 'tool.execute', tool_name: 'refund_initiate' }, decay_score: 0.46, importance: 8 },
  { id: 'evt-1-5', label: 'User: Email Pref', node_type: 'Event', session_id: 'session-1', event_type: 'observation.input', color: '#f59e0b', size: 5, ...pos(250, 0), attributes: { event_type: 'observation.input', content: 'Prefers email, team lead' }, decay_score: 0.47, importance: 6 },
  { id: 'evt-1-end', label: 'Session End', node_type: 'Event', session_id: 'session-1', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(300, 0), attributes: { event_type: 'system.session_end' }, decay_score: 0.41, importance: 2 },

  // === SESSION 2 EVENTS ===
  { id: 'evt-2-start', label: 'Session Start', node_type: 'Event', session_id: 'session-2', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 200), attributes: { event_type: 'system.session_start' }, decay_score: 0.55, importance: 3 },
  { id: 'evt-2-1', label: 'User: Kanban Question', node_type: 'Event', session_id: 'session-2', event_type: 'observation.input', color: '#f59e0b', size: 6, ...pos(80, 200), attributes: { event_type: 'observation.input', content: 'Question about Kanban board' }, decay_score: 0.58, importance: 5 },
  { id: 'evt-2-2', label: 'Agent: Welcome Back', node_type: 'Event', session_id: 'session-2', event_type: 'agent.invoke', color: '#3b82f6', size: 6, ...pos(160, 200), attributes: { event_type: 'agent.invoke' }, decay_score: 0.6, importance: 5 },
  { id: 'evt-2-3', label: 'User: Swimlane Need', node_type: 'Event', session_id: 'session-2', event_type: 'observation.input', color: '#f59e0b', size: 7, ...pos(240, 200), attributes: { event_type: 'observation.input', content: 'Need swimlane support' }, decay_score: 0.62, importance: 7 },
  { id: 'evt-2-4', label: 'User: Evaluating Taskflow', node_type: 'Event', session_id: 'session-2', event_type: 'observation.input', color: '#f59e0b', size: 7, ...pos(320, 200), attributes: { event_type: 'observation.input', content: 'Evaluating Taskflow as alternative' }, decay_score: 0.65, importance: 9 },
  { id: 'evt-2-end', label: 'Session End', node_type: 'Event', session_id: 'session-2', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(400, 200), attributes: { event_type: 'system.session_end' }, decay_score: 0.54, importance: 2 },

  // === SESSION 3 EVENTS ===
  { id: 'evt-3-start', label: 'Session Start', node_type: 'Event', session_id: 'session-3', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 400), attributes: { event_type: 'system.session_start' }, decay_score: 0.82, importance: 3 },
  { id: 'evt-3-1', label: 'User: Data Loss', node_type: 'Event', session_id: 'session-3', event_type: 'observation.input', color: '#f59e0b', size: 8, ...pos(80, 400), attributes: { event_type: 'observation.input', content: 'Kanban board lost sprint data' }, decay_score: 0.88, importance: 10 },
  { id: 'evt-3-2', label: 'Escalate Ticket', node_type: 'Event', session_id: 'session-3', event_type: 'tool.execute', color: '#22c55e', size: 7, ...pos(160, 420), attributes: { event_type: 'tool.execute', tool_name: 'escalate_ticket' }, decay_score: 0.87, importance: 9 },
  { id: 'evt-3-3', label: 'Data Recovery Check', node_type: 'Event', session_id: 'session-3', event_type: 'tool.execute', color: '#22c55e', size: 6, ...pos(160, 380), attributes: { event_type: 'tool.execute', tool_name: 'data_recovery_check' }, decay_score: 0.86, importance: 8 },
  { id: 'evt-3-4', label: 'Agent: Backup Found', node_type: 'Event', session_id: 'session-3', event_type: 'agent.invoke', color: '#3b82f6', size: 7, ...pos(240, 400), attributes: { event_type: 'agent.invoke' }, decay_score: 0.85, importance: 8 },
  { id: 'evt-3-end', label: 'Session End', node_type: 'Event', session_id: 'session-3', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(320, 400), attributes: { event_type: 'system.session_end' }, decay_score: 0.8, importance: 2 },

  // === ENTITIES ===
  { id: 'entity-sarah', label: 'Sarah Chen', node_type: 'Entity', color: '#14b8a6', size: 9, ...pos(200, 100), attributes: { entity_type: 'person', role: 'Engineering Team Lead' }, decay_score: 0.95, importance: 10 },
  { id: 'entity-nimbus', label: 'Nimbus', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(100, 100), attributes: { entity_type: 'product', plan: 'Pro' }, decay_score: 0.7, importance: 7 },
  { id: 'entity-billing', label: 'Billing System', node_type: 'Entity', color: '#14b8a6', size: 5, ...pos(150, 60), attributes: { entity_type: 'system' }, decay_score: 0.4, importance: 4 },
  { id: 'entity-refund', label: 'Refund', node_type: 'Entity', color: '#14b8a6', size: 5, ...pos(250, 60), attributes: { entity_type: 'transaction', amount: '$49.99', status: 'processed' }, decay_score: 0.45, importance: 6 },
  { id: 'entity-kanban', label: 'Kanban Board', node_type: 'Entity', color: '#14b8a6', size: 8, ...pos(200, 300), attributes: { entity_type: 'feature' }, decay_score: 0.85, importance: 9 },
  { id: 'entity-swimlanes', label: 'Swimlanes', node_type: 'Entity', color: '#14b8a6', size: 6, ...pos(300, 280), attributes: { entity_type: 'feature', status: 'Q3 roadmap' }, decay_score: 0.7, importance: 7 },
  { id: 'entity-taskflow', label: 'Taskflow', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(400, 280), attributes: { entity_type: 'competitor' }, decay_score: 0.75, importance: 8 },
  { id: 'entity-sprint-data', label: 'Sprint Data', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(100, 450), attributes: { entity_type: 'data', status: 'recovering' }, decay_score: 0.9, importance: 10 },

  // === USER PROFILE ===
  { id: 'profile-sarah', label: 'Sarah Profile', node_type: 'UserProfile', color: '#8b5cf6', size: 10, ...pos(350, 100), attributes: { name: 'Sarah Chen', role: 'Engineering Team Lead', tech_level: 'advanced', communication_style: 'direct' }, decay_score: 1.0, importance: 10 },

  // === PREFERENCES ===
  { id: 'pref-email', label: 'Prefers Email', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(400, 50), attributes: { category: 'communication', polarity: 'positive', value: 'email over phone', confidence: 0.95 }, decay_score: 0.9, importance: 7 },
  { id: 'pref-kanban', label: 'Kanban Workflow', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(350, 250), attributes: { category: 'workflow', polarity: 'positive', value: 'kanban methodology', confidence: 0.85 }, decay_score: 0.8, importance: 6 },
  { id: 'pref-nimbus', label: 'Nimbus Sentiment', node_type: 'Preference', color: '#ef4444', size: 5, ...pos(100, 350), attributes: { category: 'product', polarity: 'negative', value: 'declining satisfaction', confidence: 0.7 }, decay_score: 0.85, importance: 8 },
  { id: 'pref-taskflow', label: 'Taskflow Interest', node_type: 'Preference', color: '#6b7280', size: 4, ...pos(450, 250), attributes: { category: 'competitor', polarity: 'neutral', value: 'evaluating alternative', confidence: 0.6 }, decay_score: 0.75, importance: 7 },

  // === SKILLS ===
  { id: 'skill-leadership', label: 'Engineering Leadership', node_type: 'Skill', color: '#a855f7', size: 5, ...pos(450, 100), attributes: { proficiency: 0.9, category: 'management' }, decay_score: 0.95, importance: 6 },
  { id: 'skill-kanban', label: 'Kanban Management', node_type: 'Skill', color: '#a855f7', size: 5, ...pos(400, 180), attributes: { proficiency: 0.8, category: 'methodology' }, decay_score: 0.85, importance: 5 },

  // === SUMMARIES ===
  { id: 'summary-s1', label: 'Session 1 Summary', node_type: 'Summary', color: '#4b5563', size: 6, ...pos(150, 150), attributes: { text: 'Billing dispute resolved. Duplicate $49.99 charge refunded. Sarah prefers email communication. She is an engineering team lead.' }, decay_score: 0.5, importance: 7 },
  { id: 'summary-s2', label: 'Session 2 Summary', node_type: 'Summary', color: '#4b5563', size: 6, ...pos(250, 350), attributes: { text: 'Feature request for kanban swimlanes. Sarah evaluating Taskflow competitor. Connected to product team for early access.' }, decay_score: 0.65, importance: 8 },

  // === BEHAVIORAL PATTERN ===
  { id: 'pattern-escalation', label: 'Escalation Pattern', node_type: 'BehavioralPattern', color: '#f59e0b', size: 6, ...pos(300, 450), attributes: { pattern_type: 'escalation_tendency', observation_count: 3, confidence: 0.75, description: 'References competitor when escalating issues' }, decay_score: 0.8, importance: 7 },
];

export const mockEdges: GraphEdge[] = [
  // Session 1 FOLLOWS chain
  { id: 'e-1', source: 'evt-1-start', target: 'evt-1-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 'e-2', source: 'evt-1-1', target: 'evt-1-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 60000 } },
  { id: 'e-3', source: 'evt-1-2', target: 'evt-1-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },
  { id: 'e-4', source: 'evt-1-3', target: 'evt-1-4', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },
  { id: 'e-5', source: 'evt-1-4', target: 'evt-1-5', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },
  { id: 'e-6', source: 'evt-1-5', target: 'evt-1-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 60000 } },

  // Session 2 FOLLOWS chain
  { id: 'e-7', source: 'evt-2-start', target: 'evt-2-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 'e-8', source: 'evt-2-1', target: 'evt-2-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 60000 } },
  { id: 'e-9', source: 'evt-2-2', target: 'evt-2-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },
  { id: 'e-10', source: 'evt-2-3', target: 'evt-2-4', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 300000 } },
  { id: 'e-11', source: 'evt-2-4', target: 'evt-2-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },

  // Session 3 FOLLOWS chain
  { id: 'e-12', source: 'evt-3-start', target: 'evt-3-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 'e-13', source: 'evt-3-1', target: 'evt-3-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },
  { id: 'e-14', source: 'evt-3-1', target: 'evt-3-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },
  { id: 'e-15', source: 'evt-3-2', target: 'evt-3-4', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 360000 } },
  { id: 'e-16', source: 'evt-3-4', target: 'evt-3-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 360000 } },

  // CAUSED_BY edges
  { id: 'e-17', source: 'evt-1-2', target: 'evt-1-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 'e-18', source: 'evt-1-4', target: 'evt-1-3', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 'e-19', source: 'evt-3-2', target: 'evt-3-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 'e-20', source: 'evt-3-3', target: 'evt-3-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },

  // REFERENCES (Event -> Entity)
  { id: 'e-21', source: 'evt-1-1', target: 'entity-nimbus', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'e-22', source: 'evt-1-1', target: 'entity-billing', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'e-23', source: 'evt-1-4', target: 'entity-refund', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'e-24', source: 'evt-2-1', target: 'entity-kanban', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'e-25', source: 'evt-2-3', target: 'entity-swimlanes', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'e-26', source: 'evt-2-4', target: 'entity-taskflow', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'e-27', source: 'evt-3-1', target: 'entity-kanban', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'e-28', source: 'evt-3-1', target: 'entity-sprint-data', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },

  // SUMMARIZES
  { id: 'e-29', source: 'summary-s1', target: 'evt-1-start', edge_type: 'SUMMARIZES', color: '#4b5563', size: 1, properties: {} },
  { id: 'e-30', source: 'summary-s2', target: 'evt-2-start', edge_type: 'SUMMARIZES', color: '#4b5563', size: 1, properties: {} },

  // HAS_PROFILE
  { id: 'e-31', source: 'entity-sarah', target: 'profile-sarah', edge_type: 'HAS_PROFILE', color: '#a78bfa', size: 1, properties: {} },

  // HAS_PREFERENCE
  { id: 'e-32', source: 'entity-sarah', target: 'pref-email', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 'e-33', source: 'entity-sarah', target: 'pref-kanban', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 'e-34', source: 'entity-sarah', target: 'pref-nimbus', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 'e-35', source: 'entity-sarah', target: 'pref-taskflow', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },

  // HAS_SKILL
  { id: 'e-36', source: 'entity-sarah', target: 'skill-leadership', edge_type: 'HAS_SKILL', color: '#a78bfa', size: 1, properties: {} },
  { id: 'e-37', source: 'entity-sarah', target: 'skill-kanban', edge_type: 'HAS_SKILL', color: '#a78bfa', size: 1, properties: {} },

  // DERIVED_FROM (preferences/skills -> events)
  { id: 'e-38', source: 'pref-email', target: 'evt-1-5', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },
  { id: 'e-39', source: 'pref-kanban', target: 'evt-2-3', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },
  { id: 'e-40', source: 'pref-nimbus', target: 'evt-3-3', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },

  // EXHIBITS_PATTERN
  { id: 'e-41', source: 'entity-sarah', target: 'pattern-escalation', edge_type: 'EXHIBITS_PATTERN', color: '#f59e0b', size: 1.5, properties: {} },

  // INTERESTED_IN
  { id: 'e-42', source: 'entity-sarah', target: 'entity-kanban', edge_type: 'INTERESTED_IN', color: '#a78bfa', size: 1, properties: { weight: 0.9 } },

  // ABOUT (Preference -> Entity)
  { id: 'e-43', source: 'pref-nimbus', target: 'entity-nimbus', edge_type: 'ABOUT', color: '#a78bfa', size: 1, properties: {} },
  { id: 'e-44', source: 'pref-taskflow', target: 'entity-taskflow', edge_type: 'ABOUT', color: '#a78bfa', size: 1, properties: {} },

  // SIMILAR_TO
  { id: 'e-45', source: 'evt-2-4', target: 'evt-3-1', edge_type: 'SIMILAR_TO', color: '#60a5fa', size: 1, properties: { similarity: 0.72 } },
];
