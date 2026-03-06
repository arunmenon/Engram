export interface UserPreference {
  id: string;
  category: string;
  value: string;
  polarity: 'positive' | 'negative' | 'neutral';
  confidence: number;
  source_event_ids: string[];
  last_updated: string;
}

export interface UserSkill {
  id: string;
  name: string;
  category: string;
  proficiency: number;
  source_event_ids: string[];
}

export interface UserInterest {
  entity_id: string;
  entity_name: string;
  weight: number;
}

export interface UserPattern {
  id: string;
  pattern_type: string;
  description: string;
  observation_count: number;
  confidence: number;
  examples: string[];
}

export interface UserProfile {
  id: string;
  name: string;
  role: string;
  tech_level: string;
  communication_style: string;
  first_seen: string;
  last_seen: string;
  session_count: number;
  total_interactions: number;
}

export const sarahProfile: UserProfile = {
  id: 'profile-sarah',
  name: 'Sarah Chen',
  role: 'Engineering Team Lead',
  tech_level: 'Advanced',
  communication_style: 'Direct & professional',
  first_seen: '2024-03-01T10:00:00Z',
  last_seen: '2024-03-22T09:14:00Z',
  session_count: 3,
  total_interactions: 16,
};

export const sarahPreferences: UserPreference[] = [
  { id: 'pref-email', category: 'Communication', value: 'Prefers email over phone', polarity: 'positive', confidence: 0.95, source_event_ids: ['evt-1-5'], last_updated: '2024-03-01T10:08:00Z' },
  { id: 'pref-kanban', category: 'Workflow', value: 'Kanban methodology', polarity: 'positive', confidence: 0.85, source_event_ids: ['evt-2-3'], last_updated: '2024-03-08T14:04:00Z' },
  { id: 'pref-nimbus', category: 'Product', value: 'Declining satisfaction with Nimbus', polarity: 'negative', confidence: 0.70, source_event_ids: ['evt-3-1', 'evt-3-3'], last_updated: '2024-03-22T09:05:00Z' },
  { id: 'pref-taskflow', category: 'Competitor', value: 'Evaluating Taskflow as alternative', polarity: 'neutral', confidence: 0.60, source_event_ids: ['evt-2-5'], last_updated: '2024-03-08T14:09:00Z' },
];

export const sarahSkills: UserSkill[] = [
  { id: 'skill-leadership', name: 'Engineering Leadership', category: 'Management', proficiency: 0.9, source_event_ids: ['evt-1-5'] },
  { id: 'skill-kanban', name: 'Kanban Management', category: 'Methodology', proficiency: 0.8, source_event_ids: ['evt-2-3'] },
];

export const sarahInterests: UserInterest[] = [
  { entity_id: 'entity-kanban', entity_name: 'Kanban Board', weight: 0.9 },
  { entity_id: 'entity-swimlanes', entity_name: 'Swimlanes', weight: 0.7 },
  { entity_id: 'entity-taskflow', entity_name: 'Taskflow', weight: 0.5 },
  { entity_id: 'entity-nimbus', entity_name: 'Nimbus', weight: 0.4 },
];

export const sarahPatterns: UserPattern[] = [
  {
    id: 'pattern-escalation',
    pattern_type: 'Escalation Tendency',
    description: 'References competitor products when escalating issues, indicating churn risk',
    observation_count: 3,
    confidence: 0.75,
    examples: [
      'Mentioned evaluating Taskflow during feature request',
      'Referenced switching when reporting data loss',
      'Requested senior follow-up for critical issues',
    ],
  },
];

// Enhanced patterns matching EnhancedPattern from types/behavioral.ts
import type { EnhancedPattern } from '../types/behavioral';

export const sarahEnhancedPatterns: EnhancedPattern[] = [
  {
    id: 'pattern-escalation',
    name: 'Escalation Tendency',
    description: 'References competitor products when escalating issues, indicating churn risk',
    status: 'active',
    confidence: 0.75,
    confidence_history: [
      { date: '2024-03-01', confidence: 0.30 },
      { date: '2024-03-08', confidence: 0.55 },
      { date: '2024-03-22', confidence: 0.75 },
    ],
    observations: [
      { timestamp: '2024-03-08T14:09:00Z', session_id: 'session-2', description: 'Mentioned evaluating Taskflow as alternative', confidence_delta: 0.25 },
      { timestamp: '2024-03-22T09:05:00Z', session_id: 'session-3', description: 'Referenced switching due to data loss', confidence_delta: 0.15 },
      { timestamp: '2024-03-22T09:12:00Z', session_id: 'session-3', description: 'Requested senior follow-up for critical issue', confidence_delta: 0.05 },
    ],
    recommendations: [
      { action: 'Assign dedicated account manager', rationale: 'Proactive outreach reduces churn risk', priority: 'high' },
      { action: 'Prioritize swimlane feature delivery', rationale: 'Address competitive pressure from Taskflow', priority: 'high' },
      { action: 'Schedule quarterly business review', rationale: 'Address concerns early before escalation', priority: 'medium' },
    ],
    session_ids: ['session-2', 'session-3'],
  },
  {
    id: 'pattern-communication',
    name: 'Communication Preference',
    description: 'Consistently requests email-based follow-up, avoids phone contact',
    status: 'active',
    confidence: 0.95,
    confidence_history: [
      { date: '2024-03-01', confidence: 0.80 },
      { date: '2024-03-08', confidence: 0.90 },
      { date: '2024-03-22', confidence: 0.95 },
    ],
    observations: [
      { timestamp: '2024-03-01T10:08:00Z', session_id: 'session-1', description: 'Explicitly requested email over phone', confidence_delta: 0.80 },
      { timestamp: '2024-03-08T14:11:00Z', session_id: 'session-2', description: 'Agent confirmed email follow-up preference', confidence_delta: 0.10 },
      { timestamp: '2024-03-22T09:12:00Z', session_id: 'session-3', description: 'Requested email follow-up for postmortem', confidence_delta: 0.05 },
    ],
    recommendations: [
      { action: 'Default to email communication', rationale: 'Customer has explicitly preferred email in all sessions', priority: 'high' },
      { action: 'Include detailed written summaries', rationale: 'Engineering leads value written documentation', priority: 'medium' },
    ],
    session_ids: ['session-1', 'session-2', 'session-3'],
  },
  {
    id: 'pattern-technical-depth',
    name: 'Technical Sophistication',
    description: 'Uses precise technical terminology and expects detailed explanations',
    status: 'emerging',
    confidence: 0.60,
    confidence_history: [
      { date: '2024-03-08', confidence: 0.40 },
      { date: '2024-03-22', confidence: 0.60 },
    ],
    observations: [
      { timestamp: '2024-03-08T14:04:00Z', session_id: 'session-2', description: 'Detailed swimlane workflow requirements', confidence_delta: 0.40 },
      { timestamp: '2024-03-22T09:00:00Z', session_id: 'session-3', description: 'Precise description of data loss scenario', confidence_delta: 0.20 },
    ],
    recommendations: [
      { action: 'Provide technical root cause analysis', rationale: 'Customer expects engineering-level detail in incident reports', priority: 'medium' },
      { action: 'Skip basic troubleshooting', rationale: 'Go directly to advanced diagnostics', priority: 'low' },
    ],
    session_ids: ['session-2', 'session-3'],
  },
];
