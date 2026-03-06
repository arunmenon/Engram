import type { NodeType, EdgeType } from './atlas';

export interface GraphNode {
  id: string;
  label: string;
  node_type: NodeType;
  session_id?: string;
  event_type?: string;
  color: string;
  size: number;
  x: number;
  y: number;
  attributes: Record<string, unknown>;
  decay_score: number;
  importance: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  edge_type: EdgeType;
  color: string;
  size: number;
  label?: string;
  properties: Record<string, unknown>;
}

export const NODE_COLORS: Record<string, string> = {
  'Event:agent.invoke': '#3b82f6',
  'Event:tool.execute': '#22c55e',
  'Event:observation.input': '#f59e0b',
  'Event:system.session_start': '#6b7280',
  'Event:system.session_end': '#6b7280',
  'Entity': '#14b8a6',
  'Summary': '#4b5563',
  'UserProfile': '#8b5cf6',
  'Preference:positive': '#22c55e',
  'Preference:negative': '#ef4444',
  'Preference:neutral': '#6b7280',
  'Skill': '#a855f7',
  'Workflow': '#f59e0b',
  'BehavioralPattern': '#f59e0b',
};

export const EDGE_COLORS: Record<EdgeType, string> = {
  FOLLOWS: '#374151',
  CAUSED_BY: '#ef4444',
  SIMILAR_TO: '#60a5fa',
  REFERENCES: '#22c55e',
  SUMMARIZES: '#4b5563',
  SAME_AS: '#14b8a6',
  RELATED_TO: '#14b8a6',
  HAS_PROFILE: '#a78bfa',
  HAS_PREFERENCE: '#a78bfa',
  HAS_SKILL: '#a78bfa',
  DERIVED_FROM: '#fb923c',
  EXHIBITS_PATTERN: '#f59e0b',
  INTERESTED_IN: '#a78bfa',
  ABOUT: '#a78bfa',
  ABSTRACTED_FROM: '#f59e0b',
  PARENT_SKILL: '#a855f7',
};
