import { create } from 'zustand';
import type { GraphNode, GraphEdge } from '../types/graph';
import type { NodeType, EdgeType } from '../types/atlas';
import { mockNodes, mockEdges } from '../data/mockGraph';

interface GraphState {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  visibleNodeTypes: Set<NodeType>;
  visibleEdgeTypes: Set<EdgeType>;
  sessionFilter: string | null;
  layoutType: 'force' | 'circular';

  selectNode: (nodeId: string | null) => void;
  toggleNodeType: (nodeType: NodeType) => void;
  toggleEdgeType: (edgeType: EdgeType) => void;
  setSessionFilter: (sessionId: string | null) => void;
  setLayoutType: (layout: 'force' | 'circular') => void;
}

const allNodeTypes = new Set<NodeType>(['Event', 'Entity', 'Summary', 'UserProfile', 'Preference', 'Skill', 'Workflow', 'BehavioralPattern']);
const allEdgeTypes = new Set<EdgeType>(['FOLLOWS', 'CAUSED_BY', 'SIMILAR_TO', 'REFERENCES', 'SUMMARIZES', 'SAME_AS', 'RELATED_TO', 'HAS_PROFILE', 'HAS_PREFERENCE', 'HAS_SKILL', 'DERIVED_FROM', 'EXHIBITS_PATTERN', 'INTERESTED_IN', 'ABOUT', 'ABSTRACTED_FROM', 'PARENT_SKILL']);

export const useGraphStore = create<GraphState>((set) => ({
  nodes: mockNodes,
  edges: mockEdges,
  selectedNodeId: null,
  visibleNodeTypes: new Set(allNodeTypes),
  visibleEdgeTypes: new Set(allEdgeTypes),
  sessionFilter: null,
  layoutType: 'force',

  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),
  toggleNodeType: (nodeType) => set((state) => {
    const newTypes = new Set(state.visibleNodeTypes);
    if (newTypes.has(nodeType)) {
      newTypes.delete(nodeType);
    } else {
      newTypes.add(nodeType);
    }
    return { visibleNodeTypes: newTypes };
  }),
  toggleEdgeType: (edgeType) => set((state) => {
    const newTypes = new Set(state.visibleEdgeTypes);
    if (newTypes.has(edgeType)) {
      newTypes.delete(edgeType);
    } else {
      newTypes.add(edgeType);
    }
    return { visibleEdgeTypes: newTypes };
  }),
  setSessionFilter: (sessionId) => set({ sessionFilter: sessionId }),
  setLayoutType: (layout) => set({ layoutType: layout }),
}));
