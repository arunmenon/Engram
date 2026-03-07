import type { GraphNode, GraphEdge } from '../types/graph';
import type { ChatMessage, Session } from '../types/chat';
import type { UserProfile, UserPreference, UserSkill, UserInterest } from './mockUserProfile';
import type { EnhancedPattern } from '../types/behavioral';

// ─── Deterministic position helper ─────────────────────────────────────────
let seed = 389;
function seededRandom() {
  seed = (seed * 16807 + 0) % 2147483647;
  return (seed - 1) / 2147483646;
}
const pos = (x: number, y: number) => ({
  x: x + (seededRandom() - 0.5) * 50,
  y: y + (seededRandom() - 0.5) * 50,
});

// ─── Sessions ──────────────────────────────────────────────────────────────

export const realtySessions: Session[] = [
  {
    id: 'realty-session-1',
    title: 'Property Search',
    subtitle: 'Downtown condo with home office space',
    start_time: '2024-05-20T10:00:00Z',
    end_time: '2024-05-20T10:35:00Z',
    color: '#3b82f6',
    message_count: 6,
  },
  {
    id: 'realty-session-2',
    title: 'Mortgage Pre-Approval',
    subtitle: 'First-time buyer financing options',
    start_time: '2024-06-03T15:00:00Z',
    end_time: '2024-06-03T15:30:00Z',
    color: '#22c55e',
    message_count: 6,
  },
  {
    id: 'realty-session-3',
    title: 'Inspection Issues',
    subtitle: 'Foundation concern on 742 Elm Street',
    start_time: '2024-06-18T09:00:00Z',
    end_time: '2024-06-18T09:40:00Z',
    color: '#f59e0b',
    message_count: 6,
  },
];

// ─── Messages ──────────────────────────────────────────────────────────────

export const realtyMessages: ChatMessage[] = [
  // Session 1: Property Search
  {
    id: 'realty-msg-1-1',
    session_id: 'realty-session-1',
    role: 'user',
    content: "I'm looking for a 2-bedroom condo in downtown Austin. I work remotely so I need a dedicated home office space. Budget is around $450K.",
    timestamp: '2024-05-20T10:00:00Z',
  },
  {
    id: 'realty-msg-1-2',
    session_id: 'realty-session-1',
    role: 'agent',
    content: "Great criteria, David! Let me search our listings for 2BR condos in downtown Austin with office space in your budget range.",
    timestamp: '2024-05-20T10:02:00Z',
    tools_used: ['mls_search', 'property_filter'],
    provenance_node_ids: ['realty-evt-1-1', 'realty-entity-austin', 'realty-entity-condo'],
    context_nodes_used: 3,
  },
  {
    id: 'realty-msg-1-3',
    session_id: 'realty-session-1',
    role: 'user',
    content: "I'd prefer something built after 2015 — modern construction, good natural light. I'm a software engineer so fast internet infrastructure is a must.",
    timestamp: '2024-05-20T10:06:00Z',
  },
  {
    id: 'realty-msg-1-4',
    session_id: 'realty-session-1',
    role: 'agent',
    content: "I found 8 matching properties. Top picks: 742 Elm Street ($435K, 2BR+den, built 2019, fiber internet) and 1200 Congress Ave ($448K, 2BR+office, built 2021, rooftop terrace). Both have excellent walk scores. Want to schedule viewings?",
    timestamp: '2024-05-20T10:10:00Z',
    tools_used: ['mls_search'],
    provenance_node_ids: ['realty-entity-742elm', 'realty-entity-1200congress'],
    context_nodes_used: 4,
  },
  {
    id: 'realty-msg-1-5',
    session_id: 'realty-session-1',
    role: 'user',
    content: "Yes, both please. This is my first home purchase so I'll need guidance on the process. Can you send me details via email? I like to review things thoroughly before viewings.",
    timestamp: '2024-05-20T10:15:00Z',
  },
  {
    id: 'realty-msg-1-6',
    session_id: 'realty-session-1',
    role: 'agent',
    content: "Absolutely! I'm emailing you the full property reports with photos, floor plans, and HOA details. As a first-time buyer, I'll also include our step-by-step guide to the purchase process. Viewings scheduled for Saturday at 10am and 11:30am.",
    timestamp: '2024-05-20T10:18:00Z',
    provenance_node_ids: ['realty-pref-email', 'realty-entity-david', 'realty-pref-firstbuyer'],
    context_nodes_used: 3,
  },

  // Session 2: Mortgage Pre-Approval
  {
    id: 'realty-msg-2-1',
    session_id: 'realty-session-2',
    role: 'user',
    content: "I loved both properties from the viewings. I want to move forward with 742 Elm Street. What do I need for mortgage pre-approval?",
    timestamp: '2024-06-03T15:00:00Z',
  },
  {
    id: 'realty-msg-2-2',
    session_id: 'realty-session-2',
    role: 'agent',
    content: "Great choice, David! The 742 Elm property checks all your boxes — the den is perfect for a home office, and it has fiber internet. Let me pull up our lending partners for first-time buyer programs.",
    timestamp: '2024-06-03T15:02:00Z',
    provenance_node_ids: ['realty-entity-david', 'realty-entity-742elm', 'realty-pref-firstbuyer', 'realty-summary-s1'],
    context_nodes_used: 5,
  },
  {
    id: 'realty-msg-2-3',
    session_id: 'realty-session-2',
    role: 'user',
    content: "I have a credit score of 760 and can put 15% down. I'm interested in a 30-year fixed rate. What kind of rates am I looking at?",
    timestamp: '2024-06-03T15:07:00Z',
  },
  {
    id: 'realty-msg-2-4',
    session_id: 'realty-session-2',
    role: 'agent',
    content: "With a 760 score and 15% down on $435K, you're looking at roughly 6.2% on a 30-year fixed. Monthly payment around $2,280 including HOA. I've connected you with two preferred lenders who offer first-time buyer credits. They'll email you within 24 hours.",
    timestamp: '2024-06-03T15:12:00Z',
    tools_used: ['mortgage_calculator', 'lender_match'],
    provenance_node_ids: ['realty-entity-mortgage', 'realty-entity-742elm', 'realty-skill-finance'],
    context_nodes_used: 5,
  },
  {
    id: 'realty-msg-2-5',
    session_id: 'realty-session-2',
    role: 'user',
    content: "That monthly payment works. I've been comparing rates on Zillow and Redfin too — their estimates are slightly lower. Can your lenders beat 6.0%?",
    timestamp: '2024-06-03T15:17:00Z',
  },
  {
    id: 'realty-msg-2-6',
    session_id: 'realty-session-2',
    role: 'agent',
    content: "I'll ask both lenders to present their best rate with your profile. With your credit score and down payment, 6.0% or below is very achievable. I'll have the comparison sent to your email by tomorrow. Let's also schedule the home inspection once you're pre-approved.",
    timestamp: '2024-06-03T15:20:00Z',
    provenance_node_ids: ['realty-entity-zillow', 'realty-pref-email', 'realty-entity-david'],
    context_nodes_used: 4,
  },

  // Session 3: Inspection Issues
  {
    id: 'realty-msg-3-1',
    session_id: 'realty-session-3',
    role: 'user',
    content: "The home inspector found a potential foundation issue at 742 Elm. Hairline crack in the basement wall. I'm concerned — should I walk away?",
    timestamp: '2024-06-18T09:00:00Z',
  },
  {
    id: 'realty-msg-3-2',
    session_id: 'realty-session-3',
    role: 'agent',
    content: "I understand the concern, David. As a first-time buyer, foundation issues can feel alarming. Let me review the inspection report and connect you with our structural engineer for an expert assessment.",
    timestamp: '2024-06-18T09:03:00Z',
    tools_used: ['inspection_report_pull', 'specialist_referral'],
    provenance_node_ids: ['realty-entity-david', 'realty-entity-742elm', 'realty-pref-firstbuyer', 'realty-entity-inspection', 'realty-summary-s2'],
    context_nodes_used: 7,
  },
  {
    id: 'realty-msg-3-3',
    session_id: 'realty-session-3',
    role: 'user',
    content: "If this is going to be a money pit, I'd rather look at the Congress Ave unit or start over. I can't afford major structural repairs on top of a first mortgage.",
    timestamp: '2024-06-18T09:08:00Z',
  },
  {
    id: 'realty-msg-3-4',
    session_id: 'realty-session-3',
    role: 'agent',
    content: "Completely reasonable. Our structural engineer reviewed the photos — hairline cracks in 2019 poured concrete basements are common and typically cosmetic. But let's get an on-site assessment to be sure. If it's structural, we'll negotiate a repair credit or pivot to 1200 Congress Ave. That property is still available.",
    timestamp: '2024-06-18T09:14:00Z',
    tools_used: ['specialist_referral'],
    provenance_node_ids: ['realty-entity-inspection', 'realty-entity-1200congress', 'realty-evt-3-2'],
    context_nodes_used: 5,
  },
  {
    id: 'realty-msg-3-5',
    session_id: 'realty-session-3',
    role: 'user',
    content: "Okay, let's get the engineer out there this week. Email me the scheduling options and the full structural assessment report when it's ready.",
    timestamp: '2024-06-18T09:20:00Z',
  },
  {
    id: 'realty-msg-3-6',
    session_id: 'realty-session-3',
    role: 'agent',
    content: "Scheduled for Thursday at 2pm. I'll email you the report and assessment as soon as it's complete. Either way, you're in a strong position — 742 Elm with a possible repair credit, or 1200 Congress as a solid backup. We'll make sure you get the right home.",
    timestamp: '2024-06-18T09:24:00Z',
    provenance_node_ids: ['realty-pref-email', 'realty-entity-david', 'realty-pattern-cautious'],
    context_nodes_used: 4,
  },
];

// ─── Graph Nodes ───────────────────────────────────────────────────────────

export const realtyNodes: GraphNode[] = [
  // === SESSION 1 EVENTS ===
  { id: 'realty-evt-1-start', label: 'Session Start', node_type: 'Event', session_id: 'realty-session-1', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 0), attributes: { event_type: 'system.session_start' }, decay_score: 0.42, importance: 3 },
  { id: 'realty-evt-1-1', label: 'User: Property Search', node_type: 'Event', session_id: 'realty-session-1', event_type: 'observation.input', color: '#f59e0b', size: 6, ...pos(50, 0), attributes: { event_type: 'observation.input', content: '2BR condo downtown Austin, $450K, home office' }, decay_score: 0.45, importance: 7 },
  { id: 'realty-evt-1-2', label: 'MLS Search', node_type: 'Event', session_id: 'realty-session-1', event_type: 'tool.execute', color: '#22c55e', size: 5, ...pos(100, 20), attributes: { event_type: 'tool.execute', tool_name: 'mls_search' }, decay_score: 0.43, importance: 5 },
  { id: 'realty-evt-1-3', label: 'Properties Found', node_type: 'Event', session_id: 'realty-session-1', event_type: 'agent.invoke', color: '#3b82f6', size: 6, ...pos(150, 0), attributes: { event_type: 'agent.invoke', properties_found: 8 }, decay_score: 0.46, importance: 7 },
  { id: 'realty-evt-1-4', label: 'User: First-Time Buyer', node_type: 'Event', session_id: 'realty-session-1', event_type: 'observation.input', color: '#f59e0b', size: 5, ...pos(200, 0), attributes: { event_type: 'observation.input', content: 'First home purchase, prefers email, reviews thoroughly' }, decay_score: 0.47, importance: 6 },
  { id: 'realty-evt-1-end', label: 'Session End', node_type: 'Event', session_id: 'realty-session-1', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(250, 0), attributes: { event_type: 'system.session_end' }, decay_score: 0.41, importance: 2 },

  // === SESSION 2 EVENTS ===
  { id: 'realty-evt-2-start', label: 'Session Start', node_type: 'Event', session_id: 'realty-session-2', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 200), attributes: { event_type: 'system.session_start' }, decay_score: 0.55, importance: 3 },
  { id: 'realty-evt-2-1', label: 'User: 742 Elm Choice', node_type: 'Event', session_id: 'realty-session-2', event_type: 'observation.input', color: '#f59e0b', size: 6, ...pos(80, 200), attributes: { event_type: 'observation.input', content: 'Moving forward with 742 Elm Street' }, decay_score: 0.58, importance: 8 },
  { id: 'realty-evt-2-2', label: 'Mortgage Calculator', node_type: 'Event', session_id: 'realty-session-2', event_type: 'tool.execute', color: '#22c55e', size: 5, ...pos(160, 200), attributes: { event_type: 'tool.execute', tool_name: 'mortgage_calculator' }, decay_score: 0.60, importance: 6 },
  { id: 'realty-evt-2-3', label: 'User: Rate Shopping', node_type: 'Event', session_id: 'realty-session-2', event_type: 'observation.input', color: '#f59e0b', size: 7, ...pos(240, 200), attributes: { event_type: 'observation.input', content: 'Comparing rates on Zillow and Redfin' }, decay_score: 0.65, importance: 8 },
  { id: 'realty-evt-2-end', label: 'Session End', node_type: 'Event', session_id: 'realty-session-2', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(320, 200), attributes: { event_type: 'system.session_end' }, decay_score: 0.54, importance: 2 },

  // === SESSION 3 EVENTS ===
  { id: 'realty-evt-3-start', label: 'Session Start', node_type: 'Event', session_id: 'realty-session-3', event_type: 'system.session_start', color: '#6b7280', size: 4, ...pos(0, 400), attributes: { event_type: 'system.session_start' }, decay_score: 0.82, importance: 3 },
  { id: 'realty-evt-3-1', label: 'User: Foundation Issue', node_type: 'Event', session_id: 'realty-session-3', event_type: 'observation.input', color: '#f59e0b', size: 8, ...pos(80, 400), attributes: { event_type: 'observation.input', content: 'Foundation crack found at 742 Elm' }, decay_score: 0.88, importance: 10 },
  { id: 'realty-evt-3-2', label: 'Inspection Report Pull', node_type: 'Event', session_id: 'realty-session-3', event_type: 'tool.execute', color: '#22c55e', size: 7, ...pos(160, 420), attributes: { event_type: 'tool.execute', tool_name: 'inspection_report_pull' }, decay_score: 0.87, importance: 9 },
  { id: 'realty-evt-3-3', label: 'Specialist Referral', node_type: 'Event', session_id: 'realty-session-3', event_type: 'tool.execute', color: '#22c55e', size: 6, ...pos(160, 380), attributes: { event_type: 'tool.execute', tool_name: 'specialist_referral' }, decay_score: 0.86, importance: 8 },
  { id: 'realty-evt-3-4', label: 'Agent: Assessment Plan', node_type: 'Event', session_id: 'realty-session-3', event_type: 'agent.invoke', color: '#3b82f6', size: 7, ...pos(240, 400), attributes: { event_type: 'agent.invoke' }, decay_score: 0.85, importance: 8 },
  { id: 'realty-evt-3-end', label: 'Session End', node_type: 'Event', session_id: 'realty-session-3', event_type: 'system.session_end', color: '#6b7280', size: 4, ...pos(320, 400), attributes: { event_type: 'system.session_end' }, decay_score: 0.80, importance: 2 },

  // === ENTITIES ===
  { id: 'realty-entity-david', label: 'David Park', node_type: 'Entity', color: '#14b8a6', size: 9, ...pos(200, 100), attributes: { entity_type: 'person', role: 'Software Engineer' }, decay_score: 0.95, importance: 10 },
  { id: 'realty-entity-austin', label: 'Downtown Austin', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(100, 100), attributes: { entity_type: 'location', market: 'Austin TX' }, decay_score: 0.7, importance: 6 },
  { id: 'realty-entity-condo', label: '2BR Condo Search', node_type: 'Entity', color: '#14b8a6', size: 5, ...pos(50, 60), attributes: { entity_type: 'search_criteria', budget: '$450K' }, decay_score: 0.45, importance: 5 },
  { id: 'realty-entity-742elm', label: '742 Elm Street', node_type: 'Entity', color: '#14b8a6', size: 8, ...pos(200, 280), attributes: { entity_type: 'property', price: '$435K', year: 2019, status: 'inspection' }, decay_score: 0.90, importance: 9 },
  { id: 'realty-entity-1200congress', label: '1200 Congress Ave', node_type: 'Entity', color: '#14b8a6', size: 6, ...pos(350, 280), attributes: { entity_type: 'property', price: '$448K', year: 2021, status: 'backup' }, decay_score: 0.70, importance: 7 },
  { id: 'realty-entity-mortgage', label: 'Mortgage Pre-Approval', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(300, 200), attributes: { entity_type: 'financial', rate: '6.2%', term: '30yr fixed' }, decay_score: 0.80, importance: 8 },
  { id: 'realty-entity-zillow', label: 'Zillow/Redfin', node_type: 'Entity', color: '#14b8a6', size: 6, ...pos(400, 250), attributes: { entity_type: 'competitor' }, decay_score: 0.60, importance: 6 },
  { id: 'realty-entity-inspection', label: 'Home Inspection', node_type: 'Entity', color: '#14b8a6', size: 7, ...pos(100, 450), attributes: { entity_type: 'process', finding: 'foundation hairline crack', status: 'pending assessment' }, decay_score: 0.92, importance: 10 },

  // === USER PROFILE ===
  { id: 'realty-profile-david', label: 'David Profile', node_type: 'UserProfile', color: '#8b5cf6', size: 10, ...pos(350, 50), attributes: { name: 'David Park', role: 'Software Engineer — Remote', tech_level: 'advanced', communication_style: 'analytical & thorough' }, decay_score: 1.0, importance: 10 },

  // === PREFERENCES ===
  { id: 'realty-pref-email', label: 'Prefers Email', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(400, 10), attributes: { category: 'communication', polarity: 'positive', value: 'Email for detailed review', confidence: 0.90 }, decay_score: 0.88, importance: 6 },
  { id: 'realty-pref-firstbuyer', label: 'First-Time Buyer', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(450, 50), attributes: { category: 'experience', polarity: 'positive', value: 'Needs guided process', confidence: 0.95 }, decay_score: 0.90, importance: 7 },
  { id: 'realty-pref-modern', label: 'Modern Construction', node_type: 'Preference', color: '#22c55e', size: 5, ...pos(350, 180), attributes: { category: 'property', polarity: 'positive', value: 'Built after 2015, fiber internet', confidence: 0.90 }, decay_score: 0.85, importance: 6 },
  { id: 'realty-pref-zillow', label: 'Competitive Rates', node_type: 'Preference', color: '#6b7280', size: 4, ...pos(450, 250), attributes: { category: 'competitor', polarity: 'neutral', value: 'Comparing rates on Zillow/Redfin', confidence: 0.60 }, decay_score: 0.70, importance: 6 },

  // === SKILLS ===
  { id: 'realty-skill-tech', label: 'Software Engineering', node_type: 'Skill', color: '#a855f7', size: 5, ...pos(450, 100), attributes: { proficiency: 0.95, category: 'technical' }, decay_score: 0.90, importance: 5 },
  { id: 'realty-skill-finance', label: 'Financial Analysis', node_type: 'Skill', color: '#a855f7', size: 5, ...pos(400, 180), attributes: { proficiency: 0.70, category: 'financial' }, decay_score: 0.75, importance: 5 },

  // === SUMMARIES ===
  { id: 'realty-summary-s1', label: 'Session 1 Summary', node_type: 'Summary', color: '#4b5563', size: 6, ...pos(150, 150), attributes: { text: 'Property search: 2BR condo downtown Austin, $450K budget. First-time buyer, software engineer, needs home office. Prefers email. 742 Elm and 1200 Congress shortlisted.' }, decay_score: 0.5, importance: 7 },
  { id: 'realty-summary-s2', label: 'Session 2 Summary', node_type: 'Summary', color: '#4b5563', size: 6, ...pos(250, 330), attributes: { text: 'Chose 742 Elm Street. Mortgage pre-approval in progress. 760 credit, 15% down, targeting 6.0% rate. Comparing with Zillow/Redfin rates.' }, decay_score: 0.65, importance: 8 },

  // === BEHAVIORAL PATTERN ===
  { id: 'realty-pattern-cautious', label: 'Cautious Decision-Maker', node_type: 'BehavioralPattern', color: '#f59e0b', size: 6, ...pos(300, 450), attributes: { pattern_type: 'cautious_buyer', observation_count: 3, confidence: 0.75, description: 'Thorough researcher who compares options and needs reassurance' }, decay_score: 0.80, importance: 7 },
];

// ─── Graph Edges ───────────────────────────────────────────────────────────

export const realtyEdges: GraphEdge[] = [
  // Session 1 FOLLOWS
  { id: 're-1', source: 'realty-evt-1-start', target: 'realty-evt-1-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 're-2', source: 'realty-evt-1-1', target: 'realty-evt-1-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 120000 } },
  { id: 're-3', source: 'realty-evt-1-2', target: 'realty-evt-1-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 240000 } },
  { id: 're-4', source: 'realty-evt-1-3', target: 'realty-evt-1-4', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 300000 } },
  { id: 're-5', source: 'realty-evt-1-4', target: 'realty-evt-1-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },

  // Session 2 FOLLOWS
  { id: 're-6', source: 'realty-evt-2-start', target: 'realty-evt-2-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 're-7', source: 'realty-evt-2-1', target: 'realty-evt-2-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 420000 } },
  { id: 're-8', source: 'realty-evt-2-2', target: 'realty-evt-2-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 300000 } },
  { id: 're-9', source: 'realty-evt-2-3', target: 'realty-evt-2-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },

  // Session 3 FOLLOWS
  { id: 're-10', source: 'realty-evt-3-start', target: 'realty-evt-3-1', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 1000 } },
  { id: 're-11', source: 'realty-evt-3-1', target: 'realty-evt-3-2', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 180000 } },
  { id: 're-12', source: 'realty-evt-3-1', target: 'realty-evt-3-3', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 840000 } },
  { id: 're-13', source: 'realty-evt-3-3', target: 'realty-evt-3-4', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 360000 } },
  { id: 're-14', source: 'realty-evt-3-4', target: 'realty-evt-3-end', edge_type: 'FOLLOWS', color: '#374151', size: 1, properties: { delta_ms: 240000 } },

  // CAUSED_BY
  { id: 're-15', source: 'realty-evt-1-2', target: 'realty-evt-1-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 're-16', source: 'realty-evt-2-2', target: 'realty-evt-2-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 're-17', source: 'realty-evt-3-2', target: 'realty-evt-3-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },
  { id: 're-18', source: 'realty-evt-3-3', target: 'realty-evt-3-1', edge_type: 'CAUSED_BY', color: '#ef4444', size: 2, properties: {} },

  // REFERENCES
  { id: 're-19', source: 'realty-evt-1-1', target: 'realty-entity-austin', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 're-20', source: 'realty-evt-1-1', target: 'realty-entity-condo', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 're-21', source: 'realty-evt-1-3', target: 'realty-entity-742elm', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 're-22', source: 'realty-evt-1-3', target: 'realty-entity-1200congress', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 're-23', source: 'realty-evt-2-1', target: 'realty-entity-742elm', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 're-24', source: 'realty-evt-2-2', target: 'realty-entity-mortgage', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 're-25', source: 'realty-evt-2-3', target: 'realty-entity-zillow', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 're-26', source: 'realty-evt-3-1', target: 'realty-entity-inspection', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },
  { id: 're-27', source: 'realty-evt-3-1', target: 'realty-entity-742elm', edge_type: 'REFERENCES', color: '#22c55e', size: 1.5, properties: {} },

  // SUMMARIZES
  { id: 're-28', source: 'realty-summary-s1', target: 'realty-evt-1-start', edge_type: 'SUMMARIZES', color: '#4b5563', size: 1, properties: {} },
  { id: 're-29', source: 'realty-summary-s2', target: 'realty-evt-2-start', edge_type: 'SUMMARIZES', color: '#4b5563', size: 1, properties: {} },

  // HAS_PROFILE
  { id: 're-30', source: 'realty-entity-david', target: 'realty-profile-david', edge_type: 'HAS_PROFILE', color: '#a78bfa', size: 1, properties: {} },

  // HAS_PREFERENCE
  { id: 're-31', source: 'realty-entity-david', target: 'realty-pref-email', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 're-32', source: 'realty-entity-david', target: 'realty-pref-firstbuyer', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 're-33', source: 'realty-entity-david', target: 'realty-pref-modern', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },
  { id: 're-34', source: 'realty-entity-david', target: 'realty-pref-zillow', edge_type: 'HAS_PREFERENCE', color: '#a78bfa', size: 1, properties: {} },

  // HAS_SKILL
  { id: 're-35', source: 'realty-entity-david', target: 'realty-skill-tech', edge_type: 'HAS_SKILL', color: '#a78bfa', size: 1, properties: {} },
  { id: 're-36', source: 'realty-entity-david', target: 'realty-skill-finance', edge_type: 'HAS_SKILL', color: '#a78bfa', size: 1, properties: {} },

  // DERIVED_FROM
  { id: 're-37', source: 'realty-pref-email', target: 'realty-evt-1-4', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },
  { id: 're-38', source: 'realty-pref-firstbuyer', target: 'realty-evt-1-4', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },
  { id: 're-39', source: 'realty-pref-modern', target: 'realty-evt-1-1', edge_type: 'DERIVED_FROM', color: '#fb923c', size: 1, label: 'LLM', properties: {} },

  // EXHIBITS_PATTERN
  { id: 're-40', source: 'realty-entity-david', target: 'realty-pattern-cautious', edge_type: 'EXHIBITS_PATTERN', color: '#f59e0b', size: 1.5, properties: {} },

  // INTERESTED_IN
  { id: 're-41', source: 'realty-entity-david', target: 'realty-entity-742elm', edge_type: 'INTERESTED_IN', color: '#a78bfa', size: 1, properties: { weight: 0.95 } },
  { id: 're-42', source: 'realty-entity-david', target: 'realty-entity-1200congress', edge_type: 'INTERESTED_IN', color: '#a78bfa', size: 1, properties: { weight: 0.6 } },

  // ABOUT
  { id: 're-43', source: 'realty-pref-zillow', target: 'realty-entity-zillow', edge_type: 'ABOUT', color: '#a78bfa', size: 1, properties: {} },

  // SIMILAR_TO
  { id: 're-44', source: 'realty-evt-1-1', target: 'realty-evt-2-1', edge_type: 'SIMILAR_TO', color: '#60a5fa', size: 1, properties: { similarity: 0.75 } },
];

// ─── User Profile Data ─────────────────────────────────────────────────────

export const davidProfile: UserProfile = {
  id: 'realty-profile-david',
  name: 'David Park',
  role: 'Software Engineer — Remote Worker',
  tech_level: 'Advanced',
  communication_style: 'Analytical & thorough',
  first_seen: '2024-05-20T10:00:00Z',
  last_seen: '2024-06-18T09:24:00Z',
  session_count: 3,
  total_interactions: 18,
};

export const davidPreferences: UserPreference[] = [
  { id: 'realty-pref-email', category: 'Communication', value: 'Prefers email for detailed review', polarity: 'positive', confidence: 0.90, source_event_ids: ['realty-evt-1-4'], last_updated: '2024-05-20T10:15:00Z' },
  { id: 'realty-pref-firstbuyer', category: 'Experience', value: 'First-time buyer needs guidance', polarity: 'positive', confidence: 0.95, source_event_ids: ['realty-evt-1-4'], last_updated: '2024-05-20T10:15:00Z' },
  { id: 'realty-pref-modern', category: 'Property', value: 'Built after 2015, fiber internet required', polarity: 'positive', confidence: 0.90, source_event_ids: ['realty-evt-1-1'], last_updated: '2024-05-20T10:06:00Z' },
  { id: 'realty-pref-zillow', category: 'Competitor', value: 'Comparing rates on Zillow/Redfin', polarity: 'neutral', confidence: 0.60, source_event_ids: ['realty-evt-2-3'], last_updated: '2024-06-03T15:17:00Z' },
];

export const davidSkills: UserSkill[] = [
  { id: 'realty-skill-tech', name: 'Software Engineering', category: 'Technical', proficiency: 0.95, source_event_ids: ['realty-evt-1-1'] },
  { id: 'realty-skill-finance', name: 'Financial Analysis', category: 'Financial', proficiency: 0.70, source_event_ids: ['realty-evt-2-3'] },
];

export const davidInterests: UserInterest[] = [
  { entity_id: 'realty-entity-742elm', entity_name: '742 Elm Street', weight: 0.95 },
  { entity_id: 'realty-entity-1200congress', entity_name: '1200 Congress Ave', weight: 0.6 },
  { entity_id: 'realty-entity-mortgage', entity_name: 'Mortgage Options', weight: 0.8 },
  { entity_id: 'realty-entity-inspection', entity_name: 'Home Inspection', weight: 0.9 },
];

export const davidEnhancedPatterns: EnhancedPattern[] = [
  {
    id: 'realty-pattern-cautious',
    name: 'Cautious Decision-Maker',
    description: 'Thorough researcher who compares options across platforms and needs data-driven reassurance before committing',
    status: 'active',
    confidence: 0.75,
    confidence_history: [
      { date: '2024-05-20', confidence: 0.40 },
      { date: '2024-06-03', confidence: 0.60 },
      { date: '2024-06-18', confidence: 0.75 },
    ],
    observations: [
      { timestamp: '2024-05-20T10:15:00Z', session_id: 'realty-session-1', description: 'Reviews materials thoroughly before viewings', confidence_delta: 0.40 },
      { timestamp: '2024-06-03T15:17:00Z', session_id: 'realty-session-2', description: 'Cross-references rates on Zillow/Redfin', confidence_delta: 0.20 },
      { timestamp: '2024-06-18T09:08:00Z', session_id: 'realty-session-3', description: 'Considered walking away over inspection finding', confidence_delta: 0.15 },
    ],
    recommendations: [
      { action: 'Provide detailed comparison data proactively', rationale: 'Buyer researches independently and values data', priority: 'high' },
      { action: 'Include third-party validation in reports', rationale: 'Cross-referencing behavior suggests need for external validation', priority: 'medium' },
      { action: 'Offer guided next-step checklists', rationale: 'First-time buyer benefits from structured process', priority: 'medium' },
    ],
    session_ids: ['realty-session-1', 'realty-session-2', 'realty-session-3'],
  },
  {
    id: 'realty-pattern-email',
    name: 'Email-First Communication',
    description: 'Prefers email for all communications to review details at own pace',
    status: 'active',
    confidence: 0.90,
    confidence_history: [
      { date: '2024-05-20', confidence: 0.75 },
      { date: '2024-06-03', confidence: 0.85 },
      { date: '2024-06-18', confidence: 0.90 },
    ],
    observations: [
      { timestamp: '2024-05-20T10:15:00Z', session_id: 'realty-session-1', description: 'Requested email for property details', confidence_delta: 0.75 },
      { timestamp: '2024-06-18T09:20:00Z', session_id: 'realty-session-3', description: 'Requested email for structural assessment', confidence_delta: 0.05 },
    ],
    recommendations: [
      { action: 'Default all follow-ups to email', rationale: 'Consistent preference across all sessions', priority: 'high' },
    ],
    session_ids: ['realty-session-1', 'realty-session-3'],
  },
];
