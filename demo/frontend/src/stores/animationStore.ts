import { create } from 'zustand';
import type { TraversalStep } from '../types/chat';

export const RETRIEVAL_COLORS: Record<string, string> = {
  direct: '#3b82f6',
  proactive: '#a855f7',
  traversal: '#f59e0b',
  similar: '#06b6d4',
};

interface AnimationState {
  isAnimating: boolean;
  currentTraceIndex: number;
  activeTrace: TraversalStep[];
  animatedNodeIds: Set<string>;
  animatedEdgeIds: Set<string>;
  animationSpeed: number;

  startAnimation: (trace: TraversalStep[]) => void;
  stepAnimation: () => void;
  stopAnimation: () => void;
  resetAnimation: () => void;
  setAnimationSpeed: (speed: number) => void;
}

export const useAnimationStore = create<AnimationState>((set, get) => ({
  isAnimating: false,
  currentTraceIndex: -1,
  activeTrace: [],
  animatedNodeIds: new Set(),
  animatedEdgeIds: new Set(),
  animationSpeed: 600,

  startAnimation: (trace) =>
    set({
      isAnimating: true,
      currentTraceIndex: -1,
      activeTrace: trace,
      animatedNodeIds: new Set(),
      animatedEdgeIds: new Set(),
    }),

  stepAnimation: () => {
    const state = get();
    const nextIndex = state.currentTraceIndex + 1;
    if (nextIndex >= state.activeTrace.length) {
      set({ isAnimating: false });
      return;
    }
    const step = state.activeTrace[nextIndex];
    const newNodeIds = new Set(state.animatedNodeIds);
    const newEdgeIds = new Set(state.animatedEdgeIds);
    newNodeIds.add(step.nodeId);
    if (step.edgeId) newEdgeIds.add(step.edgeId);
    set({
      currentTraceIndex: nextIndex,
      animatedNodeIds: newNodeIds,
      animatedEdgeIds: newEdgeIds,
    });
  },

  stopAnimation: () => set({ isAnimating: false }),

  resetAnimation: () =>
    set({
      isAnimating: false,
      currentTraceIndex: -1,
      activeTrace: [],
      animatedNodeIds: new Set(),
      animatedEdgeIds: new Set(),
    }),

  setAnimationSpeed: (speed) => set({ animationSpeed: speed }),
}));
