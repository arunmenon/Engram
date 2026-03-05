export interface Provenance {
  event_id: string;
  global_position: string;
  source: 'redis' | 'neo4j' | 'llm';
  occurred_at: string;
  session_id: string;
  agent_id: string;
  trace_id: string;
}

export interface NodeScores {
  decay_score: number;
  relevance_score: number;
  importance_score: number;
  user_affinity?: number;
}

export type NodeType = 'Event' | 'Entity' | 'Summary' | 'UserProfile' | 'Preference' | 'Skill' | 'Workflow' | 'BehavioralPattern';

export type EdgeType = 'FOLLOWS' | 'CAUSED_BY' | 'SIMILAR_TO' | 'REFERENCES' | 'SUMMARIZES' | 'SAME_AS' | 'RELATED_TO' | 'HAS_PROFILE' | 'HAS_PREFERENCE' | 'HAS_SKILL' | 'DERIVED_FROM' | 'EXHIBITS_PATTERN' | 'INTERESTED_IN' | 'ABOUT' | 'ABSTRACTED_FROM' | 'PARENT_SKILL';

export type IntentType = 'why' | 'when' | 'what' | 'related' | 'general' | 'who_is' | 'how_does' | 'personalize';

export type RetrievalReason = 'direct' | 'proactive' | 'traversal' | 'similar';

export interface AtlasNode {
  id: string;
  node_type: NodeType;
  attributes: Record<string, unknown>;
  provenance: Provenance;
  scores: NodeScores;
  retrieval_reason: RetrievalReason;
}

export interface AtlasEdge {
  source: string;
  target: string;
  edge_type: EdgeType;
  properties: Record<string, unknown>;
}

export interface QueryMeta {
  query_ms: number;
  nodes_returned: number;
  truncated: boolean;
  inferred_intents: Partial<Record<IntentType, number>>;
  seed_nodes: string[];
  proactive_nodes_count: number;
  scoring_weights: {
    recency: number;
    importance: number;
    relevance: number;
    user_affinity: number;
  };
  capacity: {
    max_nodes: number;
    used_nodes: number;
    max_depth: number;
  };
}

export interface AtlasResponse {
  nodes: Record<string, AtlasNode>;
  edges: AtlasEdge[];
  meta: QueryMeta;
}
