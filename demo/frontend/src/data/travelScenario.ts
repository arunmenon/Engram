import type { GraphNode, GraphEdge } from '../types/graph';
import type { ChatMessage, Session } from '../types/chat';
import type { UserProfile, UserPreference, UserSkill, UserInterest } from './mockUserProfile';
import type { EnhancedPattern } from '../types/behavioral';

// ─── Deterministic position helper ─────────────────────────────────────────
let seed = 271;
function seededRandom() {
  seed = (seed * 16807 + 0) % 2147483647;
  return (seed - 1) / 2147483646;
}
const pos = (x: number, y: number) => ({
  x: x + (seededRandom() - 0.5) * 50,
  y: y + (seededRandom() - 0.5) * 50,
});

// ─── Sessions ──────────────────────────────────────────────────────────────

export const travelSessions: Session[] = [
  {
    id: 'travel-session-1',
    title: 'Flight Rebooking',
    subtitle: 'Dubai to London connection missed',
    start_time: '2024-06-15T06:00:00Z',
    end_time: '2024-06-15T06:30:00Z',
    color: '#3b82f6',
    message_count: 6,
  },
  {
    id: 'travel-session-2',
    title: 'Skywards Upgrade',
    subtitle: 'Business class upgrade with miles',
    start_time: '2024-06-28T18:00:00Z',
    end_time: '2024-06-28T18:25:00Z',
    color: '#22c55e',
    message_count: 6,
  },
  {
    id: 'travel-session-3',
    title: 'Lost Luggage Claim',
    subtitle: 'Delayed bags from Mumbai connection',
    start_time: '2024-07-10T22:00:00Z',
    end_time: '2024-07-10T22:35:00Z',
    color: '#f59e0b',
    message_count: 6,
  },
];

// ─── Messages ──────────────────────────────────────────────────────────────

export const travelMessages: ChatMessage[] = [
  // Session 1: Flight Rebooking
  {
    id: 'travel-msg-1-1',
    session_id: 'travel-session-1',
    role: 'user',
    content: "My EK-029 from Dubai was delayed 3 hours and I missed my London Heathrow connection. I have a business meeting tomorrow morning.",
    timestamp: '2024-06-15T06:00:00Z',
  },
  {
    id: 'travel-msg-1-2',
    session_id: 'travel-session-1',
    role: 'agent',
    content: "I'm sorry about the disruption, Priya. Let me look up your booking and find the next available connection to London.",
    timestamp: '2024-06-15T06:02:00Z',
    tools_used: ['flight_lookup', 'rebooking_search'],
    provenance_node_ids: ['travel-evt-1-1', 'travel-entity-ek029', 'travel-entity-emirates'],
    context_nodes_used: 3,
  },
  {
    id: 'travel-msg-1-3',
    session_id: 'travel-session-1',
    role: 'user',
    content: "Booking reference EK-947231. I'm Skywards Gold and I specifically need a window seat — I can't sleep in aisle seats on long flights.",
    timestamp: '2024-06-15T06:05:00Z',
  },
  {
    id: 'travel-msg-1-4',
    session_id: 'travel-session-1',
    role: 'agent',
    content: "Found your booking, Priya. I have you on EK-031 departing in 2 hours — window seat 14A in Business Class. I've also arranged access to the Business Class lounge while you wait. As a Skywards Gold member, the rebooking fee is waived.",
    timestamp: '2024-06-15T06:08:00Z',
    tools_used: ['seat_assignment', 'lounge_access'],
    provenance_node_ids: ['travel-evt-1-3', 'travel-entity-skywards', 'travel-entity-heathrow'],
    context_nodes_used: 4,
  },
  {
    id: 'travel-msg-1-5',
    session_id: 'travel-session-1',
    role: 'user',
    content: "Perfect. Can you also notify my hotel in London about the late arrival? I usually stay at the Savoy. And please send updates via WhatsApp.",
    timestamp: '2024-06-15T06:12:00Z',
  },
  {
    id: 'travel-msg-1-6',
    session_id: 'travel-session-1',
    role: 'agent',
    content: "I've notified The Savoy about your updated arrival time. All future updates will come via WhatsApp. Your new boarding pass is ready in the Emirates app. Have a smooth flight!",
    timestamp: '2024-06-15T06:14:00Z',
    provenance_node_ids: ['travel-pref-whatsapp', 'travel-entity-priya', 'travel-pref-window'],
    context_nodes_used: 3,
  },

  // Session 2: Skywards Upgrade
  {
    id: 'travel-msg-2-1',
    session_id: 'travel-session-2',
    role: 'user',
    content: "I want to use my Skywards miles to upgrade my Mumbai to Dubai flight next week to Business Class.",
    timestamp: '2024-06-28T18:00:00Z',
  },
  {
    id: 'travel-msg-2-2',
    session_id: 'travel-session-2',
    role: 'agent',
    content: "Welcome back, Priya! I hope your London meeting went well after the rebooking. Let me check upgrade availability for your Mumbai-Dubai flight.",
    timestamp: '2024-06-28T18:02:00Z',
    provenance_node_ids: ['travel-entity-priya', 'travel-entity-heathrow', 'travel-entity-skywards', 'travel-summary-s1'],
    context_nodes_used: 5,
  },
  {
    id: 'travel-msg-2-3',
    session_id: 'travel-session-2',
    role: 'user',
    content: "Flight EK-501 on July 5th. I have about 85,000 miles. Also, I need a window seat again — 1A or 2A if possible.",
    timestamp: '2024-06-28T18:06:00Z',
  },
  {
    id: 'travel-msg-2-4',
    session_id: 'travel-session-2',
    role: 'agent',
    content: "Business Class upgrade on EK-501 requires 62,500 miles. Seat 2A is available — I know you prefer window seats. Shall I process the upgrade?",
    timestamp: '2024-06-28T18:10:00Z',
    tools_used: ['miles_check', 'upgrade_availability'],
    provenance_node_ids: ['travel-entity-skywards', 'travel-pref-window', 'travel-skill-miles'],
    context_nodes_used: 4,
  },
  {
    id: 'travel-msg-2-5',
    session_id: 'travel-session-2',
    role: 'user',
    content: "Yes, process it. I fly this route monthly for work. Is there a way to auto-upgrade when Business is available?",
    timestamp: '2024-06-28T18:14:00Z',
  },
  {
    id: 'travel-msg-2-6',
    session_id: 'travel-session-2',
    role: 'agent',
    content: "Upgrade confirmed! Seat 2A on EK-501, Business Class. Regarding auto-upgrades — I've enrolled you in our Skywards Flex program which auto-bids your miles on eligible flights. I'll send confirmation via WhatsApp.",
    timestamp: '2024-06-28T18:17:00Z',
    provenance_node_ids: ['travel-pref-whatsapp', 'travel-entity-priya', 'travel-pref-business'],
    context_nodes_used: 4,
  },

  // Session 3: Lost Luggage
  {
    id: 'travel-msg-3-1',
    session_id: 'travel-session-3',
    role: 'user',
    content: "I just landed in Dubai from Mumbai and my checked luggage didn't arrive. It has my presentation materials for tomorrow's conference.",
    timestamp: '2024-07-10T22:00:00Z',
  },
  {
    id: 'travel-msg-3-2',
    session_id: 'travel-session-3',
    role: 'agent',
    content: "I'm sorry to hear this, Priya. Given your conference tomorrow, I'm treating this as urgent. Let me track your bags immediately.",
    timestamp: '2024-07-10T22:03:00Z',
    tools_used: ['baggage_trace', 'worldtracer_lookup'],
    provenance_node_ids: ['travel-entity-priya', 'travel-entity-mumbai-route', 'travel-summary-s2', 'travel-pattern-frequent'],
    context_nodes_used: 6,
  },
  {
    id: 'travel-msg-3-3',
    session_id: 'travel-session-3',
    role: 'user',
    content: "This is really stressful. If Emirates can't handle a simple Mumbai-Dubai bag transfer, I might as well try Etihad for my regular route.",
    timestamp: '2024-07-10T22:07:00Z',
  },
  {
    id: 'travel-msg-3-4',
    session_id: 'travel-session-3',
    role: 'agent',
    content: "Your bag was scanned in Mumbai and is confirmed on the next flight EK-509, arriving Dubai at 02:30. I've arranged emergency delivery to your hotel — is it The Savoy Dubai this time? Also, here's a $200 expenses allowance for emergency items.",
    timestamp: '2024-06-10T22:12:00Z',
    tools_used: ['emergency_delivery', 'compensation_issue'],
    provenance_node_ids: ['travel-entity-luggage', 'travel-evt-3-2'],
    context_nodes_used: 5,
  },
  {
    id: 'travel-msg-3-5',
    session_id: 'travel-session-3',
    role: 'user',
    content: "I'm at the Ritz-Carlton this time. Please deliver by 7am. And send me tracking updates via WhatsApp.",
    timestamp: '2024-07-10T22:18:00Z',
  },
  {
    id: 'travel-msg-3-6',
    session_id: 'travel-session-3',
    role: 'agent',
    content: "Delivery to Ritz-Carlton confirmed for 6:30am. I've set up WhatsApp tracking alerts. As a Skywards Gold member, I've also added 5,000 bonus miles to your account for the inconvenience. Your bags will be there before your conference.",
    timestamp: '2024-07-10T22:22:00Z',
    provenance_node_ids: ['travel-pref-whatsapp', 'travel-entity-priya', 'travel-entity-skywards', 'travel-pattern-frequent'],
    context_nodes_used: 4,
  },
];

// ─── Graph Nodes ───────────────────────────────────────────────────────────

export const travelNodes: GraphNode[] = [
  // === SESSION 1 EVENTS ===
  { id: 'travel-evt-1-start', label: 'Session Start', node_type: 'Event', session_id: 'travel-session-1', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 0), attributes: { event_type: 'system.session_start' }, decay_score: 0.42, importance: 3 },
  { id: 'travel-evt-1-1', label: 'User: Missed Connection', node_type: 'Event', session_id: 'travel-session-1', event_type: 'observation.input', color: '#f59e0b', size: 7, ...pos(50, 0), attributes: { event_type: 'observation.input', content: 'EK-029 delayed, missed Heathrow connection' }, decay_score: 0.45, importance: 8 },
  { id: 'travel-evt-1-2', label: 'Flight Lookup', node_type: 'Event', session_id: 'travel-session-1', event_type: 'tool.execute', color: '#22c55e', size: 5, ...pos(100, 20), attributes: { event_type: 'tool.execute', tool_name: 'flight_lookup' }, decay_score: 0.43, importance: 5 },
  { id: 'travel-evt-1-3', label: 'Rebooking Done', node_type: 'Event', session_id: 'travel-session-1', event_type: 'tool.execute', color: '#22c55e', size: 6, ...pos(150, 0), attributes: { event_type: 'tool.execute', tool_name: 'seat_assignment' }, decay_score: 0.46, importance: 8 },
  { id: 'travel-evt-1-4', label: 'User: WhatsApp Pref', node_type: 'Event', session_id: 'travel-session-1', event_type: 'observation.input', color: '#f59e0b', size: 5, ...pos(200, 0), attributes: { event_type: 'observation.input', content: 'Prefers WhatsApp, window seat, stays at Savoy' }, decay_score: 0.47, importance: 6 },
  { id: 'travel-evt-1-end', label: 'Session End', node_type: 'Event', session_id: 'travel-session-1', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(250, 0), attributes: { event_type: 'system.session_end' }, decay_score: 0.41, importance: 2 },

  // === SESSION 2 EVENTS ===
  { id: 'travel-evt-2-start', label: 'Session Start', node_type: 'Event', session_id: 'travel-session-2', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 200), attributes: { event_type: 'system.session_start' }, decay_score: 0.55, importance: 3 },
  { id: 'travel-evt-2-1', label: 'User: Miles Upgrade', node_type: 'Event', session_id: 'travel-session-2', event_type: 'observation.input', color: '#f59e0b', size: 6, ...pos(80, 200), attributes: { event_type: 'observation.input', content: 'Upgrade Mumbai-Dubai with Skywards miles' }, decay_score: 0.58, importance: 6 },
  { id: 'travel-evt-2-2', label: 'Miles Check', node_type: 'Event', session_id: 'travel-session-2', event_type: 'tool.execute', color: '#22c55e', size: 5, ...pos(160, 200), attributes: { event_type: 'tool.execute', tool_name: 'miles_check' }, decay_score: 0.60, importance: 5 },
  { id: 'travel-evt-2-3', label: 'User: Monthly Flyer', node_type: 'Event', session_id: 'travel-session-2', event_type: 'observation.input', color: '#f59e0b', size: 7, ...pos(240, 200), attributes: { event_type: 'observation.input', content: 'Flies Mumbai-Dubai monthly for work' }, decay_score: 0.65, importance: 8 },
  { id: 'travel-evt-2-end', label: 'Session End', node_type: 'Event', session_id: 'travel-session-2', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(320, 200), attributes: { event_type: 'system.session_end' }, decay_score: 0.54, importance: 2 },

  // === SESSION 3 EVENTS ===
  { id: 'travel-evt-3-start', label: 'Session Start', node_type: 'Event', session_id: 'travel-session-3', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 400), attributes: { event_type: 'system.session_start' }, decay_score: 0.82, importance: 3 },
  { id: 'travel-evt-3-1', label: 'User: Lost Luggage', node_type: 'Event', session_id: 'travel-session-3', event_type: 'observation.input', color: '#f59e0b', size: 8, ...pos(80, 400), attributes: { event_type: 'observation.input', content: 'Checked luggage missing, conference tomorrow' }, decay_score: 0.88, importance: 10 },
  { id: 'travel-evt-3-2', label: 'Baggage Trace', node_type: 'Event', session_id: 'travel-session-3', event_type: 'tool.execute', color: '#22c55e', size: 7, ...pos(160, 420), attributes: { event_type: 'tool.execute', tool_name: 'baggage_trace' }, decay_score: 0.87, importance: 9 },
  { id: 'travel-evt-3-3', label: 'Emergency Delivery', node_type: 'Event', session_id: 'travel-session-3', event_type: 'tool.execute', color: '#22c55e', size: 6, ...pos(160, 380), attributes: { event_type: 'tool.execute', tool_name: 'emergency_delivery' }, decay_score: 0.86, importance: 8 },
  { id: 'travel-evt-3-4', label: 'Compensation Issued', node_type: 'Event', session_id: 'travel-session-3', event_type: 'tool.execute', color: '#22c55e', size: 6, ...pos(240, 400), attributes: { event_type: 'tool.execute', tool_name: 'compensation_issue' }, decay_score: 0.85, importance: 7 },
  { id: 'travel-evt-3-end', label: 'Session End', node_type: 'Event', session_id: 'travel-session-3', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(320, 400), attributes: { event_type: 'system.session_end' }, decay_score: 0.80, importance: 2 },

  // === ENTITIES ===
  { id: 'travel-entity-priya', label: 'Priya Sharma', node_type: 'Entity', color: '#14b8a6', size: 9, ...pos(200, 100), attributes: { entity_type: 'person', role: 'Business Consultant' }, decay_score: 0.95, importance: 10 },
  { id: 'travel-entity-emirates', label: 'Emirates', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(100, 100), attributes: { entity_type: 'airline', tier: 'Skywards Gold' }, decay_score: 0.7, importance: 7 },
  { id: 'travel-entity-ek029', label: 'EK-029', node_type: 'Entity', color: '#14b8a6', size: 5, ...pos(50, 60), attributes: { entity_type: 'flight', route: 'Dubai-London' }, decay_score: 0.4, importance: 5 },
  { id: 'travel-entity-heathrow', label: 'London Heathrow', node_type: 'Entity', color: '#14b8a6', size: 6, ...pos(150, 60), attributes: { entity_type: 'airport', code: 'LHR' }, decay_score: 0.45, importance: 5 },
  { id: 'travel-entity-skywards', label: 'Skywards Gold', node_type: 'Entity', color: '#14b8a6', size: 8, ...pos(300, 100), attributes: { entity_type: 'loyalty', miles: 85000 }, decay_score: 0.85, importance: 9 },
  { id: 'travel-entity-mumbai-route', label: 'Mumbai-Dubai Route', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(200, 280), attributes: { entity_type: 'route', frequency: 'monthly' }, decay_score: 0.80, importance: 8 },
  { id: 'travel-entity-etihad', label: 'Etihad', node_type: 'Entity', color: '#14b8a6', size: 6, ...pos(400, 350), attributes: { entity_type: 'competitor' }, decay_score: 0.60, importance: 7 },
  { id: 'travel-entity-luggage', label: 'Lost Luggage #BT-44219', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(100, 450), attributes: { entity_type: 'incident', status: 'delivered' }, decay_score: 0.90, importance: 9 },

  // === USER PROFILE ===
  { id: 'travel-profile-priya', label: 'Priya Profile', node_type: 'UserProfile', color: '#8b5cf6', size: 10, ...pos(350, 50), attributes: { name: 'Priya Sharma', role: 'Business Consultant', tech_level: 'high', communication_style: 'professional & specific' }, decay_score: 1.0, importance: 10 },

  // === PREFERENCES ===
  { id: 'travel-pref-whatsapp', label: 'Prefers WhatsApp', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(400, 10), attributes: { category: 'communication', polarity: 'positive', value: 'WhatsApp notifications', confidence: 0.95 }, decay_score: 0.9, importance: 7 },
  { id: 'travel-pref-window', label: 'Window Seat', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(350, 180), attributes: { category: 'seating', polarity: 'positive', value: 'Always window seat', confidence: 0.95 }, decay_score: 0.92, importance: 7 },
  { id: 'travel-pref-business', label: 'Business Class', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(450, 180), attributes: { category: 'cabin', polarity: 'positive', value: 'Prefers Business Class', confidence: 0.85 }, decay_score: 0.80, importance: 6 },
  { id: 'travel-pref-etihad', label: 'Etihad Consideration', node_type: 'Preference', color: '#6b7280', size: 4, ...pos(450, 350), attributes: { category: 'competitor', polarity: 'neutral', value: 'Mentioned switching to Etihad', confidence: 0.50 }, decay_score: 0.65, importance: 6 },

  // === SKILLS ===
  { id: 'travel-skill-miles', label: 'Miles Optimization', node_type: 'Skill', color: '#a855f7', size: 5, ...pos(450, 100), attributes: { proficiency: 0.85, category: 'loyalty' }, decay_score: 0.90, importance: 6 },
  { id: 'travel-skill-travel', label: 'Frequent Travel', node_type: 'Skill', color: '#a855f7', size: 5, ...pos(300, 250), attributes: { proficiency: 0.95, category: 'experience' }, decay_score: 0.88, importance: 6 },

  // === SUMMARIES ===
  { id: 'travel-summary-s1', label: 'Session 1 Summary', node_type: 'Summary', color: '#4b5563', size: 6, ...pos(150, 150), attributes: { text: 'Missed connection rebooked. Skywards Gold, prefers window + WhatsApp. Stays at The Savoy London. Business meeting urgency.' }, decay_score: 0.5, importance: 7 },
  { id: 'travel-summary-s2', label: 'Session 2 Summary', node_type: 'Summary', color: '#4b5563', size: 6, ...pos(250, 330), attributes: { text: 'Miles upgrade processed. Flies Mumbai-Dubai monthly. Enrolled in Skywards Flex auto-upgrade program.' }, decay_score: 0.65, importance: 8 },

  // === BEHAVIORAL PATTERN ===
  { id: 'travel-pattern-frequent', label: 'High-Value Frequent Flyer', node_type: 'BehavioralPattern', color: '#f59e0b', size: 6, ...pos(300, 450), attributes: { pattern_type: 'frequent_flyer', observation_count: 3, confidence: 0.85, description: 'Monthly business traveler with specific preferences and high expectations' }, decay_score: 0.80, importance: 8 },
];

// ─── Graph Edges ───────────────────────────────────────────────────────────

export const travelEdges: GraphEdge[] = [
  // Session 1 FOLLOWS
  { id: 'te-1', source: 'travel-evt-1-start', target: 'travel-evt-1-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 'te-2', source: 'travel-evt-1-1', target: 'travel-evt-1-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },
  { id: 'te-3', source: 'travel-evt-1-2', target: 'travel-evt-1-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },
  { id: 'te-4', source: 'travel-evt-1-3', target: 'travel-evt-1-4', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 240000 } },
  { id: 'te-5', source: 'travel-evt-1-4', target: 'travel-evt-1-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },

  // Session 2 FOLLOWS
  { id: 'te-6', source: 'travel-evt-2-start', target: 'travel-evt-2-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 'te-7', source: 'travel-evt-2-1', target: 'travel-evt-2-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 240000 } },
  { id: 'te-8', source: 'travel-evt-2-2', target: 'travel-evt-2-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 240000 } },
  { id: 'te-9', source: 'travel-evt-2-3', target: 'travel-evt-2-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },

  // Session 3 FOLLOWS
  { id: 'te-10', source: 'travel-evt-3-start', target: 'travel-evt-3-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 'te-11', source: 'travel-evt-3-1', target: 'travel-evt-3-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },
  { id: 'te-12', source: 'travel-evt-3-2', target: 'travel-evt-3-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 540000 } },
  { id: 'te-13', source: 'travel-evt-3-3', target: 'travel-evt-3-4', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 360000 } },
  { id: 'te-14', source: 'travel-evt-3-4', target: 'travel-evt-3-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 600000 } },

  // CAUSED_BY
  { id: 'te-15', source: 'travel-evt-1-2', target: 'travel-evt-1-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 'te-16', source: 'travel-evt-1-3', target: 'travel-evt-1-2', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 'te-17', source: 'travel-evt-3-2', target: 'travel-evt-3-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 'te-18', source: 'travel-evt-3-3', target: 'travel-evt-3-2', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },

  // REFERENCES
  { id: 'te-19', source: 'travel-evt-1-1', target: 'travel-entity-ek029', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'te-20', source: 'travel-evt-1-1', target: 'travel-entity-heathrow', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'te-21', source: 'travel-evt-1-3', target: 'travel-entity-skywards', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'te-22', source: 'travel-evt-2-1', target: 'travel-entity-mumbai-route', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'te-23', source: 'travel-evt-2-3', target: 'travel-entity-mumbai-route', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'te-24', source: 'travel-evt-3-1', target: 'travel-entity-luggage', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 'te-25', source: 'travel-evt-3-3', target: 'travel-entity-luggage', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },

  // SUMMARIZES
  { id: 'te-26', source: 'travel-summary-s1', target: 'travel-evt-1-start', edge_type: 'SUMMARIZES', color: '#4b5563', size: 1, properties: {} },
  { id: 'te-27', source: 'travel-summary-s2', target: 'travel-evt-2-start', edge_type: 'SUMMARIZES', color: '#4b5563', size: 1, properties: {} },

  // HAS_PROFILE
  { id: 'te-28', source: 'travel-entity-priya', target: 'travel-profile-priya', edge_type: 'HAS_PROFILE', color: '#a78bfa', size: 1, properties: {} },

  // HAS_PREFERENCE
  { id: 'te-29', source: 'travel-entity-priya', target: 'travel-pref-whatsapp', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 'te-30', source: 'travel-entity-priya', target: 'travel-pref-window', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 'te-31', source: 'travel-entity-priya', target: 'travel-pref-business', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 'te-32', source: 'travel-entity-priya', target: 'travel-pref-etihad', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },

  // HAS_SKILL
  { id: 'te-33', source: 'travel-entity-priya', target: 'travel-skill-miles', edge_type: 'HAS_SKILL', color: '#a78bfa', size: 1, properties: {} },
  { id: 'te-34', source: 'travel-entity-priya', target: 'travel-skill-travel', edge_type: 'HAS_SKILL', color: '#a78bfa', size: 1, properties: {} },

  // DERIVED_FROM
  { id: 'te-35', source: 'travel-pref-whatsapp', target: 'travel-evt-1-4', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },
  { id: 'te-36', source: 'travel-pref-window', target: 'travel-evt-1-4', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },
  { id: 'te-37', source: 'travel-pref-business', target: 'travel-evt-2-3', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },

  // EXHIBITS_PATTERN
  { id: 'te-38', source: 'travel-entity-priya', target: 'travel-pattern-frequent', edge_type: 'EXHIBITS_PATTERN', color: '#f59e0b', size: 1.5, properties: {} },

  // INTERESTED_IN
  { id: 'te-39', source: 'travel-entity-priya', target: 'travel-entity-skywards', edge_type: 'INTERESTED_IN', color: '#a78bfa', size: 1, properties: { weight: 0.9 } },
  { id: 'te-40', source: 'travel-entity-priya', target: 'travel-entity-mumbai-route', edge_type: 'INTERESTED_IN', color: '#a78bfa', size: 1, properties: { weight: 0.85 } },

  // ABOUT
  { id: 'te-41', source: 'travel-pref-etihad', target: 'travel-entity-etihad', edge_type: 'ABOUT', color: '#a78bfa', size: 1, properties: {} },

  // SIMILAR_TO
  { id: 'te-42', source: 'travel-evt-1-1', target: 'travel-evt-3-1', edge_type: 'SIMILAR_TO', color: '#60a5fa', size: 1, properties: { similarity: 0.62 } },
];

// ─── User Profile Data ─────────────────────────────────────────────────────

export const priyaProfile: UserProfile = {
  id: 'travel-profile-priya',
  name: 'Priya Sharma',
  role: 'Business Consultant — Mumbai/Dubai corridor',
  tech_level: 'High',
  communication_style: 'Professional & specific',
  first_seen: '2024-06-15T06:00:00Z',
  last_seen: '2024-07-10T22:22:00Z',
  session_count: 3,
  total_interactions: 18,
};

export const priyaPreferences: UserPreference[] = [
  { id: 'travel-pref-whatsapp', category: 'Communication', value: 'Prefers WhatsApp notifications', polarity: 'positive', confidence: 0.95, source_event_ids: ['travel-evt-1-4'], last_updated: '2024-06-15T06:12:00Z' },
  { id: 'travel-pref-window', category: 'Seating', value: 'Always requests window seat', polarity: 'positive', confidence: 0.95, source_event_ids: ['travel-evt-1-3', 'travel-evt-2-3'], last_updated: '2024-06-28T18:06:00Z' },
  { id: 'travel-pref-business', category: 'Cabin', value: 'Prefers Business Class', polarity: 'positive', confidence: 0.85, source_event_ids: ['travel-evt-2-3'], last_updated: '2024-06-28T18:14:00Z' },
  { id: 'travel-pref-etihad', category: 'Competitor', value: 'Mentioned switching to Etihad', polarity: 'neutral', confidence: 0.50, source_event_ids: ['travel-evt-3-3'], last_updated: '2024-07-10T22:07:00Z' },
];

export const priyaSkills: UserSkill[] = [
  { id: 'travel-skill-miles', name: 'Miles Optimization', category: 'Loyalty', proficiency: 0.85, source_event_ids: ['travel-evt-2-1'] },
  { id: 'travel-skill-travel', name: 'Frequent Travel', category: 'Experience', proficiency: 0.95, source_event_ids: ['travel-evt-2-3'] },
];

export const priyaInterests: UserInterest[] = [
  { entity_id: 'travel-entity-skywards', entity_name: 'Skywards Gold', weight: 0.9 },
  { entity_id: 'travel-entity-mumbai-route', entity_name: 'Mumbai-Dubai Route', weight: 0.85 },
  { entity_id: 'travel-entity-etihad', entity_name: 'Etihad', weight: 0.4 },
  { entity_id: 'travel-entity-luggage', entity_name: 'Luggage Tracking', weight: 0.7 },
];

export const priyaEnhancedPatterns: EnhancedPattern[] = [
  {
    id: 'travel-pattern-frequent',
    name: 'High-Value Frequent Flyer',
    description: 'Monthly business traveler on Mumbai-Dubai route with high expectations and specific preferences',
    status: 'active',
    confidence: 0.85,
    confidence_history: [
      { date: '2024-06-15', confidence: 0.45 },
      { date: '2024-06-28', confidence: 0.70 },
      { date: '2024-07-10', confidence: 0.85 },
    ],
    observations: [
      { timestamp: '2024-06-15T06:05:00Z', session_id: 'travel-session-1', description: 'Skywards Gold member with specific seat preferences', confidence_delta: 0.45 },
      { timestamp: '2024-06-28T18:14:00Z', session_id: 'travel-session-2', description: 'Flies route monthly, knows miles optimization', confidence_delta: 0.25 },
      { timestamp: '2024-07-10T22:07:00Z', session_id: 'travel-session-3', description: 'High expectations — mentioned Etihad as alternative', confidence_delta: 0.15 },
    ],
    recommendations: [
      { action: 'Auto-assign window seats on booking', rationale: 'Consistent preference across all interactions', priority: 'high' },
      { action: 'Proactive WhatsApp flight status alerts', rationale: 'Preferred channel for all communications', priority: 'high' },
      { action: 'Priority baggage handling for Gold members', rationale: 'Lost luggage incident created churn risk', priority: 'medium' },
    ],
    session_ids: ['travel-session-1', 'travel-session-2', 'travel-session-3'],
  },
  {
    id: 'travel-pattern-communication',
    name: 'WhatsApp Communication',
    description: 'Consistently requests WhatsApp for all notifications and updates',
    status: 'active',
    confidence: 0.95,
    confidence_history: [
      { date: '2024-06-15', confidence: 0.80 },
      { date: '2024-06-28', confidence: 0.90 },
      { date: '2024-07-10', confidence: 0.95 },
    ],
    observations: [
      { timestamp: '2024-06-15T06:12:00Z', session_id: 'travel-session-1', description: 'Requested WhatsApp for flight updates', confidence_delta: 0.80 },
      { timestamp: '2024-07-10T22:18:00Z', session_id: 'travel-session-3', description: 'Requested WhatsApp for luggage tracking', confidence_delta: 0.05 },
    ],
    recommendations: [
      { action: 'Default all notifications to WhatsApp', rationale: 'Customer explicitly prefers WhatsApp in all sessions', priority: 'high' },
    ],
    session_ids: ['travel-session-1', 'travel-session-3'],
  },
];
