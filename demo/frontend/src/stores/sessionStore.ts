import { create } from 'zustand';
import type { ChatMessage, Session } from '../types/chat';
import { sessions, messages } from '../data/mockSessions';
import { useGraphStore } from './graphStore';

interface SessionState {
  sessions: Session[];
  currentSessionId: string;
  messages: ChatMessage[];
  activeEventId: string | null;
  highlightedNodeIds: string[];

  // Auto-play state
  isPlaying: boolean;
  playbackSpeed: number;
  currentStepIndex: number;
  visibleMessagesPerSession: Record<string, number>;
  autoPlayStarted: boolean;

  setCurrentSession: (sessionId: string) => void;
  setActiveEvent: (eventId: string | null) => void;
  setHighlightedNodes: (nodeIds: string[]) => void;

  // Auto-play actions
  play: () => void;
  pause: () => void;
  stepForward: () => void;
  stepBackward: () => void;
  skipToStart: () => void;
  skipToEnd: () => void;
  setPlaybackSpeed: (speed: number) => void;
  goToStep: (stepIndex: number) => void;
}

export const selectCurrentMessages = (state: SessionState) =>
  state.messages.filter(m => m.session_id === state.currentSessionId);

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions,
  currentSessionId: 'session-1',
  messages,
  activeEventId: null,
  highlightedNodeIds: [],

  // Auto-play initial state
  isPlaying: false,
  playbackSpeed: 1,
  currentStepIndex: -1,
  visibleMessagesPerSession: {},
  autoPlayStarted: false,

  setCurrentSession: (sessionId: string) => {
    set({ currentSessionId: sessionId, activeEventId: null, highlightedNodeIds: [] });
    useGraphStore.getState().setSessionFilter(sessionId);
  },
  setActiveEvent: (eventId: string | null) => set({ activeEventId: eventId }),
  setHighlightedNodes: (nodeIds: string[]) => set({ highlightedNodeIds: nodeIds }),

  play: () => {
    const state = get();
    // If starting for the first time, begin from step 0
    if (!state.autoPlayStarted) {
      const firstMsg = state.messages[0];
      if (firstMsg) {
        set({
          isPlaying: true,
          autoPlayStarted: true,
          currentStepIndex: 0,
          visibleMessagesPerSession: { [firstMsg.session_id]: 1 },
        });
        if (firstMsg.session_id !== state.currentSessionId) {
          get().setCurrentSession(firstMsg.session_id);
        }
        return;
      }
    }
    // If we've reached the end, restart
    if (state.currentStepIndex >= state.messages.length - 1) {
      const firstMsg = state.messages[0];
      if (firstMsg) {
        set({
          isPlaying: true,
          currentStepIndex: 0,
          visibleMessagesPerSession: { [firstMsg.session_id]: 1 },
        });
        if (firstMsg.session_id !== state.currentSessionId) {
          get().setCurrentSession(firstMsg.session_id);
        }
        return;
      }
    }
    set({ isPlaying: true, autoPlayStarted: true });
  },

  pause: () => set({ isPlaying: false }),

  stepForward: () => {
    const state = get();
    const nextIndex = state.currentStepIndex + 1;
    if (nextIndex >= state.messages.length) {
      set({ isPlaying: false });
      return;
    }
    const targetMsg = state.messages[nextIndex];
    const visibleCounts: Record<string, number> = {};
    for (let i = 0; i <= nextIndex; i++) {
      const sid = state.messages[i].session_id;
      visibleCounts[sid] = (visibleCounts[sid] || 0) + 1;
    }
    set({
      currentStepIndex: nextIndex,
      autoPlayStarted: true,
      visibleMessagesPerSession: visibleCounts,
    });
    if (targetMsg.session_id !== state.currentSessionId) {
      get().setCurrentSession(targetMsg.session_id);
    }
  },

  stepBackward: () => {
    const state = get();
    const prevIndex = state.currentStepIndex - 1;
    if (prevIndex < 0) return;
    const targetMsg = state.messages[prevIndex];
    const visibleCounts: Record<string, number> = {};
    for (let i = 0; i <= prevIndex; i++) {
      const sid = state.messages[i].session_id;
      visibleCounts[sid] = (visibleCounts[sid] || 0) + 1;
    }
    set({
      currentStepIndex: prevIndex,
      visibleMessagesPerSession: visibleCounts,
    });
    if (targetMsg.session_id !== state.currentSessionId) {
      get().setCurrentSession(targetMsg.session_id);
    }
  },

  skipToStart: () => {
    set({
      currentStepIndex: -1,
      isPlaying: false,
      visibleMessagesPerSession: {},
      autoPlayStarted: true,
    });
  },

  skipToEnd: () => {
    const state = get();
    const lastIndex = state.messages.length - 1;
    const visibleCounts: Record<string, number> = {};
    for (let i = 0; i <= lastIndex; i++) {
      const sid = state.messages[i].session_id;
      visibleCounts[sid] = (visibleCounts[sid] || 0) + 1;
    }
    set({
      currentStepIndex: lastIndex,
      isPlaying: false,
      visibleMessagesPerSession: visibleCounts,
    });
  },

  setPlaybackSpeed: (speed: number) => set({ playbackSpeed: speed }),

  goToStep: (stepIndex: number) => {
    const state = get();
    const targetMsg = state.messages[stepIndex];
    if (!targetMsg) return;

    const visibleCounts: Record<string, number> = {};
    for (let i = 0; i <= stepIndex; i++) {
      const sid = state.messages[i].session_id;
      visibleCounts[sid] = (visibleCounts[sid] || 0) + 1;
    }

    set({
      currentStepIndex: stepIndex,
      autoPlayStarted: true,
      isPlaying: false,
      visibleMessagesPerSession: visibleCounts,
    });

    if (targetMsg.session_id !== state.currentSessionId) {
      get().setCurrentSession(targetMsg.session_id);
    }
  },
}));
