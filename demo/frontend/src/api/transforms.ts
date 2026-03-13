import type { AtlasResponse } from "../types/atlas";
import type { GraphNode, GraphEdge } from "../types/graph";

export const NODE_COLORS: Record<string, string> = {
  Event: "#3b82f6",
  Entity: "#14b8a6",
  Summary: "#4b5563",
  UserProfile: "#8b5cf6",
  Preference: "#22c55e",
  Skill: "#a855f7",
  Workflow: "#f59e0b",
  BehavioralPattern: "#f59e0b",
  Belief: "#f97316",
  Goal: "#06b6d4",
  Episode: "#6366f1",
};

/** Event subtype colors -- visually distinguish event_type within Event nodes */
const EVENT_SUBTYPE_COLORS: Record<string, string> = {
  "system.session_start": "#94a3b8", // slate-400 (muted, boundary marker)
  "system.session_end": "#94a3b8",   // slate-400
  "observation.input": "#60a5fa",    // blue-400 (customer messages, brighter)
  "agent.invoke": "#818cf8",         // indigo-400 (agent activation)
  "tool.execute": "#c084fc",         // purple-400 (tool usage, distinct)
  "observation.output": "#38bdf8",   // sky-400 (agent responses)
};

/** Event subtype sizes -- larger for content-rich events, smaller for markers */
const EVENT_SUBTYPE_SIZES: Record<string, number> = {
  "system.session_start": 4,
  "system.session_end": 4,
  "observation.input": 8,
  "agent.invoke": 7,
  "tool.execute": 7,
  "observation.output": 8,
};

export function getEventColor(eventType: string | undefined): string {
  if (!eventType) return NODE_COLORS.Event;
  return EVENT_SUBTYPE_COLORS[eventType] ?? NODE_COLORS.Event;
}

export function getEventSize(eventType: string | undefined): number {
  if (!eventType) return 6;
  return EVENT_SUBTYPE_SIZES[eventType] ?? 6;
}

const EDGE_COLORS: Record<string, string> = {
  FOLLOWS: "#64748b",
  CAUSED_BY: "#f87171",
  SIMILAR_TO: "#60a5fa",
  REFERENCES: "#22c55e",
  SUMMARIZES: "#6b7280",
  SAME_AS: "#14b8a6",
  RELATED_TO: "#8b5cf6",
  HAS_PROFILE: "#a855f7",
  HAS_PREFERENCE: "#22c55e",
  HAS_SKILL: "#a855f7",
  DERIVED_FROM: "#f59e0b",
  EXHIBITS_PATTERN: "#f59e0b",
  INTERESTED_IN: "#14b8a6",
  ABOUT: "#22c55e",
  ABSTRACTED_FROM: "#f59e0b",
  PARENT_SKILL: "#a855f7",
  CONTAINS: "#6366f1",
  CONTRADICTS: "#ef4444",
  PURSUES: "#06b6d4",
  SUPERSEDES: "#f97316",
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
    color:
      node.node_type === "Event"
        ? getEventColor(node.attributes.event_type as string | undefined)
        : (NODE_COLORS[node.node_type] ?? "#6b7280"),
    size:
      node.node_type === "Event"
        ? getEventSize(node.attributes.event_type as string | undefined)
        : 8,
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
    color: EDGE_COLORS[edge.edge_type] ?? "#64748b",
    size: edge.edge_type === "CAUSED_BY" ? 2.5 : 1.5,
    label: edge.edge_type,
    properties: edge.properties,
  }));

  return { nodes, edges };
}
