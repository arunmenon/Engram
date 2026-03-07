import { create } from 'zustand';
import type Sigma from 'sigma';
import type { GraphNode, GraphEdge } from '../types/graph';
import type { NodeType, EdgeType, AtlasResponse, QueryMeta } from '../types/atlas';
import { mockNodes, mockEdges } from '../data/mockGraph';
import { tracker } from '../analytics/tracker';
import { useAnnounceStore } from './announceStore';
import { apiGet, apiPost } from '../api/client';
import { transformAtlasResponse } from '../api/transforms';
import { isLiveMode, isSimulatorMode } from '../api/mode';

interface GraphState {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  visibleNodeTypes: Set<NodeType>;
  visibleEdgeTypes: Set<EdgeType>;
  sessionFilter: string | null;
  layoutType: 'force' | 'circular';
  sigmaRenderer: Sigma | null;
  loading: boolean;
  error: string | null;
  lastAtlasMeta: QueryMeta | null;

  selectNode: (nodeId: string | null) => void;
  toggleNodeType: (nodeType: NodeType) => void;
  toggleEdgeType: (edgeType: EdgeType) => void;
  setSessionFilter: (sessionId: string | null) => void;
  setLayoutType: (layout: 'force' | 'circular') => void;
  setSigmaRenderer: (renderer: Sigma | null) => void;
  setGraphData: (nodes: GraphNode[], edges: GraphEdge[], meta?: QueryMeta | null) => void;
  fetchSessionContext: (sessionId: string) => Promise<void>;
  fetchSubgraph: (query: string, sessionId?: string) => Promise<void>;
}

const allNodeTypes = new Set<NodeType>(['Event', 'Entity', 'Summary', 'UserProfile', 'Preference', 'Skill', 'Workflow', 'BehavioralPattern']);
const allEdgeTypes = new Set<EdgeType>(['FOLLOWS', 'CAUSED_BY', 'SIMILAR_TO', 'REFERENCES', 'SUMMARIZES', 'SAME_AS', 'RELATED_TO', 'HAS_PROFILE', 'HAS_PREFERENCE', 'HAS_SKILL', 'DERIVED_FROM', 'EXHIBITS_PATTERN', 'INTERESTED_IN', 'ABOUT', 'ABSTRACTED_FROM', 'PARENT_SKILL']);

export const useGraphStore = create<GraphState>((set, get) => ({
  nodes: isSimulatorMode() ? [] : mockNodes,
  edges: isSimulatorMode() ? [] : mockEdges,
  selectedNodeId: null,
  visibleNodeTypes: new Set(allNodeTypes),
  visibleEdgeTypes: new Set(allEdgeTypes),
  sessionFilter: null,
  layoutType: 'force',
  sigmaRenderer: null,
  loading: false,
  error: null,
  lastAtlasMeta: null,

  setGraphData: (nodes, edges, meta = null) => {
    set({ nodes, edges, lastAtlasMeta: meta ?? null, loading: false, error: null });
  },

  fetchSessionContext: async (sessionId) => {
    if (!isLiveMode()) return;
    set({ loading: true, error: null });
    try {
      const atlas = await apiGet<AtlasResponse>(`/v1/context/${sessionId}`);
      const { nodes, edges } = transformAtlasResponse(atlas);
      set({ nodes, edges, lastAtlasMeta: atlas.meta, loading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch context', loading: false });
    }
  },

  fetchSubgraph: async (query, sessionId) => {
    if (!isLiveMode()) return;
    set({ loading: true, error: null });
    try {
      const body: Record<string, unknown> = { query };
      if (sessionId) body.session_id = sessionId;
      const atlas = await apiPost<AtlasResponse>('/v1/query/subgraph', body);
      const { nodes, edges } = transformAtlasResponse(atlas);
      set({ nodes, edges, lastAtlasMeta: atlas.meta, loading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch subgraph', loading: false });
    }
  },

  selectNode: (nodeId) => {
    tracker.track({ type: 'node.click', nodeId: nodeId ?? '', nodeType: '' });
    set({ selectedNodeId: nodeId });
    if (nodeId) {
      const node = get().nodes.find(n => n.id === nodeId);
      useAnnounceStore.getState().announce(`Selected: ${node?.label ?? nodeId}`);
    } else {
      useAnnounceStore.getState().announce('Selection cleared');
    }
  },
  toggleNodeType: (nodeType) => {
    const wasEnabled = get().visibleNodeTypes.has(nodeType);
    set((state) => {
      const newTypes = new Set(state.visibleNodeTypes);
      if (wasEnabled) {
        newTypes.delete(nodeType);
      } else {
        newTypes.add(nodeType);
      }
      return { visibleNodeTypes: newTypes };
    });
    tracker.track({ type: 'filter.toggle', filterType: 'node', value: nodeType, enabled: !wasEnabled });
    useAnnounceStore.getState().announce(`${nodeType} nodes ${wasEnabled ? 'hidden' : 'shown'}`);
  },
  toggleEdgeType: (edgeType) => set((state) => {
    const newTypes = new Set(state.visibleEdgeTypes);
    const wasEnabled = newTypes.has(edgeType);
    if (wasEnabled) {
      newTypes.delete(edgeType);
    } else {
      newTypes.add(edgeType);
    }
    tracker.track({ type: 'filter.toggle', filterType: 'edge', value: edgeType, enabled: !wasEnabled });
    return { visibleEdgeTypes: newTypes };
  }),
  setSessionFilter: (sessionId) => set({ sessionFilter: sessionId }),
  setLayoutType: (layout) => {
    tracker.track({ type: 'graph.layout_change', layout });
    set({ layoutType: layout });
  },
  setSigmaRenderer: (renderer) => set({ sigmaRenderer: renderer }),
}));
