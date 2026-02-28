import { create } from 'zustand';
import {
  getScenarios,
  startSession,
  sendMessage,
  type ScenarioInfo,
} from '../api/orchestrator';
import { useGraphStore } from './graphStore';

interface LiveMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  context_used?: number;
  inferred_intents?: Record<string, number>;
}

interface ChatState {
  scenarios: ScenarioInfo[];
  activeScenario: ScenarioInfo | null;
  sessionId: string | null;
  messages: LiveMessage[];
  isStreaming: boolean;
  error: string | null;

  fetchScenarios: () => Promise<void>;
  startScenario: (scenarioId: string) => Promise<void>;
  sendUserMessage: (content: string) => Promise<void>;
  resetChat: () => void;
}

let messageId = 0;

export const useChatStore = create<ChatState>((set, get) => ({
  scenarios: [],
  activeScenario: null,
  sessionId: null,
  messages: [],
  isStreaming: false,
  error: null,

  fetchScenarios: async () => {
    try {
      const scenarios = await getScenarios();
      set({ scenarios });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Failed to fetch scenarios',
      });
    }
  },

  startScenario: async (scenarioId) => {
    try {
      set({ isStreaming: true, error: null, messages: [] });
      const { session_id, scenario } = await startSession(scenarioId);
      set({
        sessionId: session_id,
        activeScenario: scenario,
        isStreaming: false,
      });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Failed to start scenario',
        isStreaming: false,
      });
    }
  },

  sendUserMessage: async (content) => {
    const state = get();
    if (!state.sessionId || !state.activeScenario) return;

    const userMsg: LiveMessage = {
      id: `live-msg-${++messageId}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    set((s) => ({
      messages: [...s.messages, userMsg],
      isStreaming: true,
      error: null,
    }));

    try {
      const response = await sendMessage(
        state.sessionId,
        content,
        state.activeScenario.id,
      );

      const agentMsg: LiveMessage = {
        id: `live-msg-${++messageId}`,
        role: 'agent',
        content: response.agent_message,
        timestamp: new Date().toISOString(),
        context_used: response.context_used,
        inferred_intents: response.inferred_intents,
      };

      set((s) => ({ messages: [...s.messages, agentMsg], isStreaming: false }));

      // Refresh the graph after each message
      useGraphStore.getState().fetchSessionContext(state.sessionId);
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Failed to send message',
        isStreaming: false,
      });
    }
  },

  resetChat: () =>
    set({
      activeScenario: null,
      sessionId: null,
      messages: [],
      error: null,
    }),
}));
