export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  tools_used?: string[];
  provenance_node_ids?: string[];
  context_nodes_used?: number;
}

export interface Session {
  id: string;
  title: string;
  subtitle: string;
  start_time: string;
  end_time: string;
  color: string;
  message_count: number;
}

export interface ScenarioStep {
  session_id: string;
  message_index: number;
  description: string;
}
