import type { AtlasResponse } from '../types/atlas';
import type { GraphNode, GraphEdge } from '../types/graph';

const NODE_COLORS: Record<string, string> = {
  Event: '#3b82f6',
  Entity: '#14b8a6',
  Summary: '#4b5563',
  UserProfile: '#8b5cf6',
  Preference: '#22c55e',
  Skill: '#a855f7',
  Workflow: '#f59e0b',
  BehavioralPattern: '#f59e0b',
};

const EDGE_COLORS: Record<string, string> = {
  FOLLOWS: '#374151',
  CAUSED_BY: '#ef4444',
  SIMILAR_TO: '#60a5fa',
  REFERENCES: '#22c55e',
  SUMMARIZES: '#6b7280',
  SAME_AS: '#14b8a6',
  RELATED_TO: '#8b5cf6',
  HAS_PROFILE: '#a855f7',
  HAS_PREFERENCE: '#22c55e',
  HAS_SKILL: '#a855f7',
  DERIVED_FROM: '#f59e0b',
  EXHIBITS_PATTERN: '#f59e0b',
  INTERESTED_IN: '#14b8a6',
  ABOUT: '#22c55e',
  ABSTRACTED_FROM: '#f59e0b',
  PARENT_SKILL: '#a855f7',
};

export function transformAtlasResponse(atlas: AtlasResponse): {
  nodes: GraphNode[];
  edges: GraphEdge[];
} {
  const entries = Object.entries(atlas.nodes);
  const nodeCount = entries.length;

  const nodes: GraphNode[] = entries.map(([id, node], i) => ({
    id,
    label: (node.attributes.label as string) ?? id,
    node_type: node.node_type,
    session_id: node.provenance?.session_id,
    event_type: node.attributes.event_type as string | undefined,
    color: NODE_COLORS[node.node_type] ?? '#6b7280',
    size: node.node_type === 'Event' ? 6 : 8,
    x: Math.cos((2 * Math.PI * i) / nodeCount) * 200,
    y: Math.sin((2 * Math.PI * i) / nodeCount) * 200,
    attributes: node.attributes,
    decay_score: node.scores.decay_score,
    importance: node.scores.importance_score,
  }));

  const edges: GraphEdge[] = atlas.edges.map((edge, i) => ({
    id: `edge-${i}`,
    source: edge.source,
    target: edge.target,
    edge_type: edge.edge_type,
    color: EDGE_COLORS[edge.edge_type] ?? '#374151',
    size: 1,
    label: edge.edge_type,
    properties: edge.properties,
  }));

  return { nodes, edges };
}
