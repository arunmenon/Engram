import type { GraphNode, GraphEdge } from '../types/graph';
import type { ChatMessage, Session } from '../types/chat';
import type { UserProfile, UserPreference, UserSkill, UserInterest } from './mockUserProfile';
import type { EnhancedPattern } from '../types/behavioral';

// ─── Deterministic position helper ─────────────────────────────────────────
let seed = 137;
function seededRandom() {
  seed = (seed * 16807 + 0) % 2147483647;
  return (seed - 1) / 2147483646;
}
const pos = (x: number, y: number) => ({
  x: x + (seededRandom() - 0.5) * 50,
  y: y + (seededRandom() - 0.5) * 50,
});

// ─── Sessions ──────────────────────────────────────────────────────────────

export const merchantSessions: Session[] = [
  {
    id: 'merch-session-1',
    title: 'Chargeback Dispute',
    subtitle: 'Fraudulent chargeback on $2,400 order',
    start_time: '2024-04-10T09:00:00Z',
    end_time: '2024-04-10T09:30:00Z',
    color: '#3b82f6',
    message_count: 6,
  },
  {
    id: 'merch-session-2',
    title: 'API Integration Help',
    subtitle: 'Webhook setup for order notifications',
    start_time: '2024-04-18T14:00:00Z',
    end_time: '2024-04-18T14:25:00Z',
    color: '#22c55e',
    message_count: 6,
  },
  {
    id: 'merch-session-3',
    title: 'Settlement Delay',
    subtitle: 'Funds held — risk review escalation',
    start_time: '2024-05-02T11:00:00Z',
    end_time: '2024-05-02T11:35:00Z',
    color: '#f59e0b',
    message_count: 6,
  },
];

// ─── Messages ──────────────────────────────────────────────────────────────

export const merchantMessages: ChatMessage[] = [
  // Session 1: Chargeback Dispute
  {
    id: 'merch-msg-1-1',
    session_id: 'merch-session-1',
    role: 'user',
    content: "I just got a chargeback on a $2,400 bulk order that I already shipped. The buyer received the goods — I have tracking proof.",
    timestamp: '2024-04-10T09:00:00Z',
  },
  {
    id: 'merch-msg-1-2',
    session_id: 'merch-session-1',
    role: 'agent',
    content: "I understand how frustrating that is, Marcus. Let me pull up the transaction and chargeback details for your account.",
    timestamp: '2024-04-10T09:02:00Z',
    tools_used: ['transaction_lookup', 'chargeback_details'],
    provenance_node_ids: ['merch-evt-1-1', 'merch-entity-chargeback', 'merch-entity-paypal'],
    context_nodes_used: 3,
  },
  {
    id: 'merch-msg-1-3',
    session_id: 'merch-session-1',
    role: 'user',
    content: "Order #PP-78234. Shipped via FedEx, delivered April 5th. I have the signed delivery confirmation.",
    timestamp: '2024-04-10T09:05:00Z',
  },
  {
    id: 'merch-msg-1-4',
    session_id: 'merch-session-1',
    role: 'agent',
    content: "I found the transaction. The buyer filed an 'item not received' claim, but your FedEx tracking shows delivered with signature. I'm submitting your evidence to the chargeback response team — this looks very winnable.",
    timestamp: '2024-04-10T09:08:00Z',
    tools_used: ['chargeback_evidence_submit'],
    provenance_node_ids: ['merch-evt-1-3', 'merch-entity-chargeback', 'merch-entity-fedex'],
    context_nodes_used: 4,
  },
  {
    id: 'merch-msg-1-5',
    session_id: 'merch-session-1',
    role: 'user',
    content: "Good. I run a custom furniture shop and these chargebacks kill my cash flow. Can you keep me posted via text? I'm usually in the workshop.",
    timestamp: '2024-04-10T09:12:00Z',
  },
  {
    id: 'merch-msg-1-6',
    session_id: 'merch-session-1',
    role: 'agent',
    content: "Absolutely — I'll set up SMS notifications for your chargeback updates. The response team typically resolves these within 10 business days. Your tracking evidence is strong.",
    timestamp: '2024-04-10T09:14:00Z',
    provenance_node_ids: ['merch-pref-sms', 'merch-entity-marcus'],
    context_nodes_used: 2,
  },

  // Session 2: API Integration Help
  {
    id: 'merch-msg-2-1',
    session_id: 'merch-session-2',
    role: 'user',
    content: "Hey, I need help setting up PayPal webhooks for my Shopify store. I want real-time order notifications.",
    timestamp: '2024-04-18T14:00:00Z',
  },
  {
    id: 'merch-msg-2-2',
    session_id: 'merch-session-2',
    role: 'agent',
    content: "Welcome back, Marcus! Good news — your chargeback from last week was resolved in your favor. For the webhook setup, are you using PayPal's REST API or the IPN system?",
    timestamp: '2024-04-18T14:02:00Z',
    provenance_node_ids: ['merch-entity-marcus', 'merch-entity-chargeback', 'merch-entity-shopify', 'merch-summary-s1'],
    context_nodes_used: 5,
  },
  {
    id: 'merch-msg-2-3',
    session_id: 'merch-session-2',
    role: 'user',
    content: "REST API. I need to catch PAYMENT.CAPTURE.COMPLETED and PAYMENT.CAPTURE.REFUNDED events. My developer set up the endpoint but we're not receiving events.",
    timestamp: '2024-04-18T14:06:00Z',
  },
  {
    id: 'merch-msg-2-4',
    session_id: 'merch-session-2',
    role: 'agent',
    content: "I can see your webhook configuration. The endpoint URL is correct but it's returning 403 on our verification POST. Your server needs to respond to the webhook verification challenge with a 200 status. I'll send you the code snippet.",
    timestamp: '2024-04-18T14:10:00Z',
    tools_used: ['webhook_diagnostic'],
    provenance_node_ids: ['merch-entity-webhook', 'merch-entity-rest-api', 'merch-skill-api'],
    context_nodes_used: 4,
  },
  {
    id: 'merch-msg-2-5',
    session_id: 'merch-session-2',
    role: 'user',
    content: "That makes sense. We're also looking at Stripe as a backup processor because of all the hold issues we've had. Can PayPal match their webhook reliability?",
    timestamp: '2024-04-18T14:15:00Z',
  },
  {
    id: 'merch-msg-2-6',
    session_id: 'merch-session-2',
    role: 'agent',
    content: "Our webhook delivery rate is 99.9% with automatic retries. I understand the concern about holds — I'll flag your account for our merchant success team to review your hold frequency. Sending the verification code snippet via text now.",
    timestamp: '2024-04-18T14:18:00Z',
    provenance_node_ids: ['merch-entity-stripe', 'merch-pref-sms', 'merch-entity-marcus'],
    context_nodes_used: 4,
  },

  // Session 3: Settlement Delay
  {
    id: 'merch-msg-3-1',
    session_id: 'merch-session-3',
    role: 'user',
    content: "My settlement from last week is being held. That's $8,500 in funds I need to pay my lumber supplier. This keeps happening.",
    timestamp: '2024-05-02T11:00:00Z',
  },
  {
    id: 'merch-msg-3-2',
    session_id: 'merch-session-3',
    role: 'agent',
    content: "I see the hold on your account, Marcus. Given your history — the resolved chargeback and your mention of evaluating Stripe — I'm escalating this immediately to our risk review team. Let me check the hold reason.",
    timestamp: '2024-05-02T11:03:00Z',
    tools_used: ['settlement_lookup', 'risk_review_check'],
    provenance_node_ids: ['merch-entity-marcus', 'merch-entity-stripe', 'merch-entity-chargeback', 'merch-pattern-cashflow', 'merch-summary-s2'],
    context_nodes_used: 7,
  },
  {
    id: 'merch-msg-3-3',
    session_id: 'merch-session-3',
    role: 'user',
    content: "This is exactly why small businesses leave PayPal. I can't have my operating capital frozen every other week.",
    timestamp: '2024-05-02T11:07:00Z',
  },
  {
    id: 'merch-msg-3-4',
    session_id: 'merch-session-3',
    role: 'agent',
    content: "Completely understand. The hold was triggered by a volume spike — your sales grew 40% this month, which is great but triggered our automated review. I've requested an expedited release. Your funds should be available within 24 hours.",
    timestamp: '2024-05-02T11:12:00Z',
    tools_used: ['expedite_settlement'],
    provenance_node_ids: ['merch-entity-settlement', 'merch-evt-3-2'],
    context_nodes_used: 5,
  },
  {
    id: 'merch-msg-3-5',
    session_id: 'merch-session-3',
    role: 'user',
    content: "Fine. But I need someone from your merchant team to set up a higher threshold so this doesn't happen again. Text me when the funds release.",
    timestamp: '2024-05-02T11:18:00Z',
  },
  {
    id: 'merch-msg-3-6',
    session_id: 'merch-session-3',
    role: 'agent',
    content: "Done. I've submitted a threshold increase request and scheduled a call with our merchant success team for Friday. I'll text you as soon as the funds are released. Your account has been flagged for priority processing going forward.",
    timestamp: '2024-05-02T11:22:00Z',
    provenance_node_ids: ['merch-pref-sms', 'merch-entity-marcus', 'merch-pattern-cashflow'],
    context_nodes_used: 4,
  },
];

// ─── Graph Nodes ───────────────────────────────────────────────────────────

export const merchantNodes: GraphNode[] = [
  // === SESSION 1 EVENTS ===
  { id: 'merch-evt-1-start', label: 'Session Start', node_type: 'Event', session_id: 'merch-session-1', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 0), attributes: { event_type: 'system.session_start' }, decay_score: 0.42, importance: 3 },
  { id: 'merch-evt-1-1', label: 'User: Chargeback Report', node_type: 'Event', session_id: 'merch-session-1', event_type: 'observation.input', color: '#f59e0b', size: 6, ...pos(50, 0), attributes: { event_type: 'observation.input', content: '$2,400 chargeback on shipped order' }, decay_score: 0.45, importance: 8 },
  { id: 'merch-evt-1-2', label: 'Transaction Lookup', node_type: 'Event', session_id: 'merch-session-1', event_type: 'tool.execute', color: '#22c55e', size: 5, ...pos(100, 20), attributes: { event_type: 'tool.execute', tool_name: 'transaction_lookup' }, decay_score: 0.43, importance: 5 },
  { id: 'merch-evt-1-3', label: 'Evidence Submitted', node_type: 'Event', session_id: 'merch-session-1', event_type: 'tool.execute', color: '#22c55e', size: 6, ...pos(150, 0), attributes: { event_type: 'tool.execute', tool_name: 'chargeback_evidence_submit' }, decay_score: 0.46, importance: 8 },
  { id: 'merch-evt-1-4', label: 'User: SMS Pref', node_type: 'Event', session_id: 'merch-session-1', event_type: 'observation.input', color: '#f59e0b', size: 5, ...pos(200, 0), attributes: { event_type: 'observation.input', content: 'Prefers SMS, runs furniture shop' }, decay_score: 0.47, importance: 6 },
  { id: 'merch-evt-1-end', label: 'Session End', node_type: 'Event', session_id: 'merch-session-1', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(250, 0), attributes: { event_type: 'system.session_end' }, decay_score: 0.41, importance: 2 },

  // === SESSION 2 EVENTS ===
  { id: 'merch-evt-2-start', label: 'Session Start', node_type: 'Event', session_id: 'merch-session-2', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 200), attributes: { event_type: 'system.session_start' }, decay_score: 0.55, importance: 3 },
  { id: 'merch-evt-2-1', label: 'User: Webhook Help', node_type: 'Event', session_id: 'merch-session-2', event_type: 'observation.input', color: '#f59e0b', size: 6, ...pos(80, 200), attributes: { event_type: 'observation.input', content: 'Need webhook setup for Shopify' }, decay_score: 0.58, importance: 6 },
  { id: 'merch-evt-2-2', label: 'Webhook Diagnostic', node_type: 'Event', session_id: 'merch-session-2', event_type: 'tool.execute', color: '#22c55e', size: 5, ...pos(160, 200), attributes: { event_type: 'tool.execute', tool_name: 'webhook_diagnostic' }, decay_score: 0.60, importance: 5 },
  { id: 'merch-evt-2-3', label: 'User: Stripe Mention', node_type: 'Event', session_id: 'merch-session-2', event_type: 'observation.input', color: '#f59e0b', size: 7, ...pos(240, 200), attributes: { event_type: 'observation.input', content: 'Evaluating Stripe as backup' }, decay_score: 0.65, importance: 9 },
  { id: 'merch-evt-2-end', label: 'Session End', node_type: 'Event', session_id: 'merch-session-2', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(320, 200), attributes: { event_type: 'system.session_end' }, decay_score: 0.54, importance: 2 },

  // === SESSION 3 EVENTS ===
  { id: 'merch-evt-3-start', label: 'Session Start', node_type: 'Event', session_id: 'merch-session-3', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 400), attributes: { event_type: 'system.session_start' }, decay_score: 0.82, importance: 3 },
  { id: 'merch-evt-3-1', label: 'User: Funds Held', node_type: 'Event', session_id: 'merch-session-3', event_type: 'observation.input', color: '#f59e0b', size: 8, ...pos(80, 400), attributes: { event_type: 'observation.input', content: '$8,500 settlement held' }, decay_score: 0.88, importance: 10 },
  { id: 'merch-evt-3-2', label: 'Risk Review Check', node_type: 'Event', session_id: 'merch-session-3', event_type: 'tool.execute', color: '#22c55e', size: 7, ...pos(160, 420), attributes: { event_type: 'tool.execute', tool_name: 'risk_review_check' }, decay_score: 0.87, importance: 9 },
  { id: 'merch-evt-3-3', label: 'Expedite Settlement', node_type: 'Event', session_id: 'merch-session-3', event_type: 'tool.execute', color: '#22c55e', size: 6, ...pos(160, 380), attributes: { event_type: 'tool.execute', tool_name: 'expedite_settlement' }, decay_score: 0.86, importance: 8 },
  { id: 'merch-evt-3-4', label: 'Agent: Funds Released', node_type: 'Event', session_id: 'merch-session-3', event_type: 'agent.invoke', color: '#3b82f6', size: 7, ...pos(240, 400), attributes: { event_type: 'agent.invoke' }, decay_score: 0.85, importance: 8 },
  { id: 'merch-evt-3-end', label: 'Session End', node_type: 'Event', session_id: 'merch-session-3', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(320, 400), attributes: { event_type: 'system.session_end' }, decay_score: 0.80, importance: 2 },

  // === ENTITIES ===
  { id: 'merch-entity-marcus', label: 'Marcus Rivera', node_type: 'Entity', color: '#14b8a6', size: 9, ...pos(200, 100), attributes: { entity_type: 'person', role: 'Small Business Owner' }, decay_score: 0.95, importance: 10 },
  { id: 'merch-entity-paypal', label: 'PayPal', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(100, 100), attributes: { entity_type: 'platform', plan: 'Business' }, decay_score: 0.7, importance: 7 },
  { id: 'merch-entity-chargeback', label: 'Chargeback #CB-78234', node_type: 'Entity', color: '#14b8a6', size: 6, ...pos(150, 60), attributes: { entity_type: 'dispute', amount: '$2,400', status: 'won' }, decay_score: 0.5, importance: 8 },
  { id: 'merch-entity-fedex', label: 'FedEx Tracking', node_type: 'Entity', color: '#14b8a6', size: 5, ...pos(250, 60), attributes: { entity_type: 'evidence', carrier: 'FedEx' }, decay_score: 0.4, importance: 5 },
  { id: 'merch-entity-shopify', label: 'Shopify Store', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(100, 280), attributes: { entity_type: 'platform' }, decay_score: 0.65, importance: 6 },
  { id: 'merch-entity-webhook', label: 'Webhook Config', node_type: 'Entity', color: '#14b8a6', size: 6, ...pos(200, 280), attributes: { entity_type: 'integration', status: '403 error' }, decay_score: 0.60, importance: 6 },
  { id: 'merch-entity-rest-api', label: 'REST API', node_type: 'Entity', color: '#14b8a6', size: 5, ...pos(300, 280), attributes: { entity_type: 'technology' }, decay_score: 0.58, importance: 5 },
  { id: 'merch-entity-stripe', label: 'Stripe', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(400, 280), attributes: { entity_type: 'competitor' }, decay_score: 0.75, importance: 8 },
  { id: 'merch-entity-settlement', label: 'Settlement Hold', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(100, 450), attributes: { entity_type: 'financial', amount: '$8,500', status: 'released' }, decay_score: 0.90, importance: 10 },

  // === USER PROFILE ===
  { id: 'merch-profile-marcus', label: 'Marcus Profile', node_type: 'UserProfile', color: '#8b5cf6', size: 10, ...pos(350, 100), attributes: { name: 'Marcus Rivera', role: 'Small Business Owner', tech_level: 'intermediate', communication_style: 'direct & urgent' }, decay_score: 1.0, importance: 10 },

  // === PREFERENCES ===
  { id: 'merch-pref-sms', label: 'Prefers SMS', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(400, 50), attributes: { category: 'communication', polarity: 'positive', value: 'SMS over email', confidence: 0.95 }, decay_score: 0.9, importance: 7 },
  { id: 'merch-pref-cashflow', label: 'Cash Flow Priority', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(350, 250), attributes: { category: 'business', polarity: 'positive', value: 'Fast settlement critical', confidence: 0.90 }, decay_score: 0.85, importance: 8 },
  { id: 'merch-pref-stripe', label: 'Stripe Interest', node_type: 'Preference', color: '#6b7280', size: 4, ...pos(450, 250), attributes: { category: 'competitor', polarity: 'neutral', value: 'Evaluating Stripe as backup', confidence: 0.65 }, decay_score: 0.75, importance: 7 },
  { id: 'merch-pref-paypal', label: 'PayPal Frustration', node_type: 'Preference', color: '#ef4444', size: 5, ...pos(100, 350), attributes: { category: 'platform', polarity: 'negative', value: 'Frustrated with fund holds', confidence: 0.80 }, decay_score: 0.85, importance: 8 },

  // === SKILLS ===
  { id: 'merch-skill-ecommerce', label: 'E-commerce Operations', node_type: 'Skill', color: '#a855f7', size: 5, ...pos(450, 100), attributes: { proficiency: 0.8, category: 'business' }, decay_score: 0.90, importance: 6 },
  { id: 'merch-skill-api', label: 'API Integration', node_type: 'Skill', color: '#a855f7', size: 5, ...pos(400, 180), attributes: { proficiency: 0.5, category: 'technical' }, decay_score: 0.70, importance: 5 },

  // === SUMMARIES ===
  { id: 'merch-summary-s1', label: 'Session 1 Summary', node_type: 'Summary', color: '#4b5563', size: 6, ...pos(150, 150), attributes: { text: 'Chargeback dispute on $2,400 order. Evidence submitted — tracking shows delivered. Marcus prefers SMS. Runs custom furniture business.' }, decay_score: 0.5, importance: 7 },
  { id: 'merch-summary-s2', label: 'Session 2 Summary', node_type: 'Summary', color: '#4b5563', size: 6, ...pos(250, 350), attributes: { text: 'Webhook integration help for Shopify. 403 verification error diagnosed. Marcus evaluating Stripe as backup processor due to hold issues.' }, decay_score: 0.65, importance: 8 },

  // === BEHAVIORAL PATTERN ===
  { id: 'merch-pattern-cashflow', label: 'Cash Flow Sensitivity', node_type: 'BehavioralPattern', color: '#f59e0b', size: 6, ...pos(300, 450), attributes: { pattern_type: 'cash_flow_sensitivity', observation_count: 3, confidence: 0.80, description: 'Cash flow disruptions trigger churn risk' }, decay_score: 0.80, importance: 8 },
];

// ─── Graph Edges ───────────────────────────────────────────────────────────

export const merchantEdges: GraphEdge[] = [
  // Session 1 FOLLOWS chain
  { id: 'me-1', source: 'merch-evt-1-start', target: 'merch-evt-1-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 'me-2', source: 'merch-evt-1-1', target: 'merch-evt-1-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },
  { id: 'me-3', source: 'merch-evt-1-2', target: 'merch-evt-1-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },
  { id: 'me-4', source: 'merch-evt-1-3', target: 'merch-evt-1-4', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 240000 } },
  { id: 'me-5', source: 'merch-evt-1-4', target: 'merch-evt-1-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },

  // Session 2 FOLLOWS chain
  { id: 'me-6', source: 'merch-evt-2-start', target: 'merch-evt-2-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 'me-7', source: 'merch-evt-2-1', target: 'merch-evt-2-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 240000 } },
  { id: 'me-8', source: 'merch-evt-2-2', target: 'merch-evt-2-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 300000 } },
  { id: 'me-9', source: 'merch-evt-2-3', target: 'merch-evt-2-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },

  // Session 3 FOLLOWS chain
  { id: 'me-10', source: 'merch-evt-3-start', target: 'merch-evt-3-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 'me-11', source: 'merch-evt-3-1', target: 'merch-evt-3-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },
  { id: 'me-12', source: 'merch-evt-3-1', target: 'merch-evt-3-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 720000 } },
  { id: 'me-13', source: 'merch-evt-3-3', target: 'merch-evt-3-4', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 600000 } },
  { id: 'me-14', source: 'merch-evt-3-4', target: 'merch-evt-3-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 240000 } },

  // CAUSED_BY edges
  { id: 'me-15', source: 'merch-evt-1-2', target: 'merch-evt-1-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 'me-16', source: 'merch-evt-1-3', target: 'merch-evt-1-2', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 'me-17', source: 'merch-evt-3-2', target: 'merch-evt-3-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 'me-18', source: 'merch-evt-3-3', target: 'merch-evt-3-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },

  // REFERENCES (Event -> Entity)
  { id: 'me-19', source: 'merch-evt-1-1', target: 'merch-entity-chargeback', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'me-20', source: 'merch-evt-1-1', target: 'merch-entity-paypal', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'me-21', source: 'merch-evt-1-3', target: 'merch-entity-fedex', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'me-22', source: 'merch-evt-2-1', target: 'merch-entity-shopify', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'me-23', source: 'merch-evt-2-2', target: 'merch-entity-webhook', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'me-24', source: 'merch-evt-2-3', target: 'merch-entity-stripe', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'me-25', source: 'merch-evt-3-1', target: 'merch-entity-settlement', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },

  // SUMMARIZES
  { id: 'me-26', source: 'merch-summary-s1', target: 'merch-evt-1-start', edge_type: 'SUMMARIZES', color: '#4b5563', size: 1, properties: {} },
  { id: 'me-27', source: 'merch-summary-s2', target: 'merch-evt-2-start', edge_type: 'SUMMARIZES', color: '#4b5563', size: 1, properties: {} },

  // HAS_PROFILE
  { id: 'me-28', source: 'merch-entity-marcus', target: 'merch-profile-marcus', edge_type: 'HAS_PROFILE', color: '#a78bfa', size: 1, properties: {} },

  // HAS_PREFERENCE
  { id: 'me-29', source: 'merch-entity-marcus', target: 'merch-pref-sms', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 'me-30', source: 'merch-entity-marcus', target: 'merch-pref-cashflow', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 'me-31', source: 'merch-entity-marcus', target: 'merch-pref-paypal', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 'me-32', source: 'merch-entity-marcus', target: 'merch-pref-stripe', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },

  // HAS_SKILL
  { id: 'me-33', source: 'merch-entity-marcus', target: 'merch-skill-ecommerce', edge_type: 'HAS_SKILL', color: '#a78bfa', size: 1, properties: {} },
  { id: 'me-34', source: 'merch-entity-marcus', target: 'merch-skill-api', edge_type: 'HAS_SKILL', color: '#a78bfa', size: 1, properties: {} },

  // DERIVED_FROM (preferences -> events)
  { id: 'me-35', source: 'merch-pref-sms', target: 'merch-evt-1-4', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },
  { id: 'me-36', source: 'merch-pref-cashflow', target: 'merch-evt-3-1', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },
  { id: 'me-37', source: 'merch-pref-paypal', target: 'merch-evt-3-3', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },

  // EXHIBITS_PATTERN
  { id: 'me-38', source: 'merch-entity-marcus', target: 'merch-pattern-cashflow', edge_type: 'EXHIBITS_PATTERN', color: '#f59e0b', size: 1.5, properties: {} },

  // INTERESTED_IN
  { id: 'me-39', source: 'merch-entity-marcus', target: 'merch-entity-shopify', edge_type: 'INTERESTED_IN', color: '#a78bfa', size: 1, properties: { weight: 0.8 } },

  // ABOUT
  { id: 'me-40', source: 'merch-pref-stripe', target: 'merch-entity-stripe', edge_type: 'ABOUT', color: '#a78bfa', size: 1, properties: {} },
  { id: 'me-41', source: 'merch-pref-paypal', target: 'merch-entity-paypal', edge_type: 'ABOUT', color: '#a78bfa', size: 1, properties: {} },

  // SIMILAR_TO
  { id: 'me-42', source: 'merch-evt-1-1', target: 'merch-evt-3-1', edge_type: 'SIMILAR_TO', color: '#60a5fa', size: 1, properties: { similarity: 0.68 } },
];

// ─── User Profile Data ─────────────────────────────────────────────────────

export const marcusProfile: UserProfile = {
  id: 'merch-profile-marcus',
  name: 'Marcus Rivera',
  role: 'Small Business Owner — Custom Furniture',
  tech_level: 'Intermediate',
  communication_style: 'Direct & urgent',
  first_seen: '2024-04-10T09:00:00Z',
  last_seen: '2024-05-02T11:22:00Z',
  session_count: 3,
  total_interactions: 18,
};

export const marcusPreferences: UserPreference[] = [
  { id: 'merch-pref-sms', category: 'Communication', value: 'Prefers SMS over email', polarity: 'positive', confidence: 0.95, source_event_ids: ['merch-evt-1-4'], last_updated: '2024-04-10T09:12:00Z' },
  { id: 'merch-pref-cashflow', category: 'Business', value: 'Fast settlement is critical', polarity: 'positive', confidence: 0.90, source_event_ids: ['merch-evt-3-1'], last_updated: '2024-05-02T11:00:00Z' },
  { id: 'merch-pref-stripe', category: 'Competitor', value: 'Evaluating Stripe as backup', polarity: 'neutral', confidence: 0.65, source_event_ids: ['merch-evt-2-3'], last_updated: '2024-04-18T14:15:00Z' },
  { id: 'merch-pref-paypal', category: 'Platform', value: 'Frustrated with PayPal fund holds', polarity: 'negative', confidence: 0.80, source_event_ids: ['merch-evt-3-1', 'merch-evt-3-3'], last_updated: '2024-05-02T11:07:00Z' },
];

export const marcusSkills: UserSkill[] = [
  { id: 'merch-skill-ecommerce', name: 'E-commerce Operations', category: 'Business', proficiency: 0.8, source_event_ids: ['merch-evt-1-1'] },
  { id: 'merch-skill-api', name: 'API Integration', category: 'Technical', proficiency: 0.5, source_event_ids: ['merch-evt-2-1'] },
];

export const marcusInterests: UserInterest[] = [
  { entity_id: 'merch-entity-shopify', entity_name: 'Shopify Store', weight: 0.8 },
  { entity_id: 'merch-entity-webhook', entity_name: 'Webhooks', weight: 0.6 },
  { entity_id: 'merch-entity-stripe', entity_name: 'Stripe', weight: 0.5 },
  { entity_id: 'merch-entity-settlement', entity_name: 'Settlements', weight: 0.9 },
];

export const marcusEnhancedPatterns: EnhancedPattern[] = [
  {
    id: 'merch-pattern-cashflow',
    name: 'Cash Flow Sensitivity',
    description: 'Cash flow disruptions trigger competitive evaluation and churn risk signals',
    status: 'active',
    confidence: 0.80,
    confidence_history: [
      { date: '2024-04-10', confidence: 0.35 },
      { date: '2024-04-18', confidence: 0.55 },
      { date: '2024-05-02', confidence: 0.80 },
    ],
    observations: [
      { timestamp: '2024-04-10T09:12:00Z', session_id: 'merch-session-1', description: 'Chargebacks hurt cash flow — mentioned impact on business', confidence_delta: 0.35 },
      { timestamp: '2024-04-18T14:15:00Z', session_id: 'merch-session-2', description: 'Mentioned Stripe as backup due to hold issues', confidence_delta: 0.20 },
      { timestamp: '2024-05-02T11:07:00Z', session_id: 'merch-session-3', description: 'Explicitly threatened leaving over settlement delays', confidence_delta: 0.25 },
    ],
    recommendations: [
      { action: 'Enable priority settlement processing', rationale: 'Cash flow is critical for SMB retention', priority: 'high' },
      { action: 'Assign dedicated merchant success manager', rationale: 'Proactive outreach reduces competitive evaluation', priority: 'high' },
      { action: 'Increase automated hold thresholds', rationale: 'Growth-triggered holds harm established merchants', priority: 'medium' },
    ],
    session_ids: ['merch-session-1', 'merch-session-2', 'merch-session-3'],
  },
  {
    id: 'merch-pattern-communication',
    name: 'SMS Communication Preference',
    description: 'Consistently requests text/SMS updates, usually in workshop away from email',
    status: 'active',
    confidence: 0.95,
    confidence_history: [
      { date: '2024-04-10', confidence: 0.80 },
      { date: '2024-04-18', confidence: 0.90 },
      { date: '2024-05-02', confidence: 0.95 },
    ],
    observations: [
      { timestamp: '2024-04-10T09:12:00Z', session_id: 'merch-session-1', description: 'Requested SMS — usually in workshop', confidence_delta: 0.80 },
      { timestamp: '2024-05-02T11:18:00Z', session_id: 'merch-session-3', description: 'Repeated request for text notification on fund release', confidence_delta: 0.05 },
    ],
    recommendations: [
      { action: 'Default all notifications to SMS', rationale: 'Customer explicitly prefers text over email', priority: 'high' },
    ],
    session_ids: ['merch-session-1', 'merch-session-3'],
  },
];
