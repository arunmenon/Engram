import { create } from 'zustand';
import { useGraphStore } from './graphStore';

export type InsightTab = 'context' | 'user' | 'scores' | 'api' | 'debug';

interface InsightState {
  activeTab: InsightTab;
  debugEnabled: boolean;

  setActiveTab: (tab: InsightTab) => void;
  toggleDebug: () => void;
  /** @deprecated Use graphStore.selectNode instead. Delegates to graphStore. */
  setSelectedNode: (nodeId: string | null) => void;
}

export const useInsightStore = create<InsightState>((set, get) => ({
  activeTab: 'context',
  debugEnabled: false,

  setActiveTab: (tab) => set({ activeTab: tab }),
  toggleDebug: () => {
    const next = !get().debugEnabled;
    set({ debugEnabled: next });
    if (!next && get().activeTab === 'debug') {
      set({ activeTab: 'context' });
    }
  },
  setSelectedNode: (nodeId) => useGraphStore.getState().selectNode(nodeId),
}));
