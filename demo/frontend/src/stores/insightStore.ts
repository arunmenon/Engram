import { create } from 'zustand';
import { useGraphStore } from './graphStore';

type InsightTab = 'context' | 'user' | 'scores' | 'api';

interface InsightState {
  activeTab: InsightTab;

  setActiveTab: (tab: InsightTab) => void;
  /** @deprecated Use graphStore.selectNode instead. Delegates to graphStore. */
  setSelectedNode: (nodeId: string | null) => void;
}

export const useInsightStore = create<InsightState>((set) => ({
  activeTab: 'context',

  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedNode: (nodeId) => useGraphStore.getState().selectNode(nodeId),
}));
