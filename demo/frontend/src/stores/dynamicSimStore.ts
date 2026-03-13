/**
 * Zustand store for dynamic two-agent conversation simulation.
 *
 * Unlike the scripted simulatorStore, this drives real-time LLM-powered
 * conversations between two personas, streaming responses token-by-token
 * and ingesting each turn through the full Engram pipeline.
 */
import { create } from "zustand";
import type { Persona } from "../data/personas";
import { useGraphStore } from "./graphStore";
import {
  EngramError,
  messageToEvents,
  simulateTurnStream,
  type EventPayload,
  type SimulateTurnDone,
} from "../api/engram";
import {
  type PipelineStats,
  EMPTY_PIPELINE_STATS,
  getSharedClient,
  detectBackend,
  fetchPipelineStats,
  fetchLiveGraph,
  fetchLiveUserData,
  clearUserStoreData,
} from "../api/pipeline";

// Re-export PipelineStats for consumers that imported it from here
export type { PipelineStats };

/**
 * Retrieve past context from the Engram graph and format it as a system
 * prompt supplement for the support agent.  Returns an empty string when
 * no meaningful prior context exists.
 */
async function _retrievePastContext(
  _sessionId: string,
  customerName: string,
): Promise<string> {
  try {
    const client = getSharedClient();

    // Query cross-session user data (preferences, skills, interests)
    // The extraction consumer creates user entities keyed by agent_id,
    // so the entity in Neo4j is "user:fe-dynamic-sim" (not the persona name).
    const userId = "user:fe-dynamic-sim";
    const [prefsRes, skillsRes, interestsRes] = await Promise.allSettled([
      client.getUserPreferences(userId),
      client.getUserSkills(userId),
      client.getUserInterests(userId),
    ]);

    const parts: string[] = [];

    if (prefsRes.status === "fulfilled" && Array.isArray(prefsRes.value)) {
      const items = prefsRes.value
        .map((p: Record<string, unknown>) => {
          const key = (p.key as string) ?? "";
          const context = (p.context as string) ?? "";
          return context || key.replace(/_/g, " ");
        })
        .filter(Boolean);
      if (items.length) parts.push("Customer preferences: " + items.join("; "));
    }

    if (skillsRes.status === "fulfilled" && Array.isArray(skillsRes.value)) {
      const names = skillsRes.value
        .map((s: Record<string, unknown>) => (s.name as string) ?? "")
        .filter(Boolean);
      if (names.length) parts.push("Customer skills: " + names.join(", "));
    }

    if (
      interestsRes.status === "fulfilled" &&
      Array.isArray(interestsRes.value)
    ) {
      const names = interestsRes.value
        .map((i: Record<string, unknown>) => (i.name as string) ?? "")
        .filter(Boolean);
      if (names.length) parts.push("Customer interests: " + names.join(", "));
    }

    if (parts.length === 0) return "";

    return (
      "\n\n--- CUSTOMER HISTORY (from Engram context graph) ---\n" +
      `The following context was retrieved about ${customerName} from previous sessions:\n` +
      parts.join("\n") +
      "\n\nUse this context naturally in your responses. Reference past interactions when relevant " +
      "to show continuity and personalized service. Do NOT list these facts back mechanically.\n" +
      "--- END CUSTOMER HISTORY ---"
    );
  } catch {
    // Context retrieval is best-effort; don't block the conversation
    return "";
  }
}

// ─── Types ──────────────────────────────────────────────────────────────────

export type DynamicStatus =
  | "picking"
  | "ready"
  | "generating"
  | "ingesting"
  | "waiting"
  | "paused"
  | "complete"
  | "error";

export interface DynamicMessage {
  id: string;
  role: "customer" | "support";
  personaName: string;
  personaAvatar: string;
  personaColor: string;
  content: string;
  timestamp: string;
  turnId?: string;
  modelId?: string;
  tokensUsed?: number;
}

interface DynamicSimState {
  status: DynamicStatus;
  customerPersona: Persona | null;
  supportPersona: Persona | null;
  topicSeed: string;
  sessionId: string;
  turnCount: number;
  maxTurns: number;
  messages: DynamicMessage[];
  streamingContent: string;
  streamingPersona: Persona | null;
  isAutoPlaying: boolean;
  turnDelayMs: number;

  // Pipeline state
  backendConnected: boolean;
  ingestedEvents: number;
  pipelineStats: PipelineStats;
  lastApiError: string | null;
  isClearing: boolean;
  isReconsolidating: boolean;

  // Trace ID for session lifecycle (start/end must share the same trace)
  _sessionTraceId: string;

  // Actions
  enterPicker: () => void;
  selectPersonas: (
    customer: Persona,
    support: Persona,
    topic: string,
    maxTurns?: number,
  ) => void;
  generateNextTurn: () => Promise<void>;
  startAutoPlay: () => void;
  pauseAutoPlay: () => void;
  endSession: () => Promise<void>;
  setTurnDelay: (ms: number) => void;
  setMaxTurns: (n: number) => void;
  clearContextGraph: () => Promise<void>;
  triggerReconsolidate: () => Promise<void>;
  refreshPipelineStats: () => Promise<void>;
  reset: () => void;
}

// ─── Generation Lock ─────────────────────────────────────────────────────────

let _generationLock = false;
let _abortController: AbortController | null = null;

// ─── Store ──────────────────────────────────────────────────────────────────

export const useDynamicSimStore = create<DynamicSimState>((set, get) => ({
  status: "picking",
  customerPersona: null,
  supportPersona: null,
  topicSeed: "",
  sessionId: "",
  turnCount: 0,
  maxTurns: 20,
  messages: [],
  streamingContent: "",
  streamingPersona: null,
  isAutoPlaying: false,
  turnDelayMs: 1500,
  backendConnected: false,
  ingestedEvents: 0,
  pipelineStats: EMPTY_PIPELINE_STATS,
  lastApiError: null,
  isClearing: false,
  isReconsolidating: false,
  _sessionTraceId: "",

  enterPicker: () => {
    if (_abortController) _abortController.abort();
    _abortController = null;
    _generationLock = false;
    set({
      status: "picking",
      customerPersona: null,
      supportPersona: null,
      topicSeed: "",
      sessionId: "",
      turnCount: 0,
      messages: [],
      streamingContent: "",
      streamingPersona: null,
      isAutoPlaying: false,
      backendConnected: false,
      ingestedEvents: 0,
      pipelineStats: EMPTY_PIPELINE_STATS,
      lastApiError: null,
      _sessionTraceId: "",
    });
    useGraphStore.getState().setGraphData([], []);
    clearUserStoreData();
  },

  selectPersonas: (customer, support, topic, maxTurns) => {
    const sessionId = `dynamic-${Date.now()}`;
    const traceId = crypto.randomUUID();
    set({
      status: "ready",
      customerPersona: customer,
      supportPersona: support,
      topicSeed: topic,
      sessionId,
      turnCount: 0,
      maxTurns: maxTurns ?? 20,
      messages: [],
      streamingContent: "",
      streamingPersona: null,
      isAutoPlaying: false,
      ingestedEvents: 0,
      lastApiError: null,
      pipelineStats: EMPTY_PIPELINE_STATS,
      _sessionTraceId: traceId,
    });
    useGraphStore.getState().setGraphData([], []);

    // Detect backend
    detectBackend().then(async (available) => {
      if (available) {
        // Ingest session_start with stored trace_id
        const startTime = new Date().toISOString();
        try {
          const startEvent: EventPayload = {
            event_id: crypto.randomUUID(),
            event_type: "system.session_start",
            occurred_at: startTime,
            session_id: sessionId,
            agent_id: "fe-dynamic-sim",
            trace_id: traceId,
            payload_ref: `inline://session-start-${sessionId}`,
            importance_hint: 3,
            status: "completed",
          };
          await getSharedClient().ingestBatch([startEvent]);
        } catch {
          // Non-critical
        }

        const stats = await fetchPipelineStats();
        set({
          backendConnected: true,
          lastApiError: null,
          pipelineStats: stats,
        });
      } else {
        set({
          backendConnected: false,
          lastApiError:
            "Engram backend not available. Start with: docker compose -f docker/docker-compose.yml up -d",
        });
      }
    });
  },

  generateNextTurn: async () => {
    const state = get();
    if (!state.customerPersona || !state.supportPersona) return;
    if (_generationLock) return;
    _generationLock = true;

    try {
      if (state.turnCount >= state.maxTurns) {
        await get().endSession();
        return;
      }

      // Determine speaker: even turns = customer, odd = support
      const isCustomerTurn = state.turnCount % 2 === 0;
      const activePersona = isCustomerTurn
        ? state.customerPersona
        : state.supportPersona;

      const abortController = new AbortController();
      _abortController = abortController;
      set({
        status: "generating",
        streamingContent: "",
        streamingPersona: activePersona,
        lastApiError: null,
      });

      // Build conversation history with perspective flip
      // LLM always sees itself as "assistant" and the other party as "user"
      const currentMessages = get().messages;
      const history = currentMessages.map((msg) => ({
        role: msg.role === activePersona.role ? "assistant" : "user",
        content: msg.content,
      }));

      // Augment support agent's system prompt with retrieved context
      let augmentedPrompt = activePersona.systemPrompt;
      if (
        activePersona.role === "support" &&
        state.backendConnected &&
        state.customerPersona
      ) {
        const pastContext = await _retrievePastContext(
          state.sessionId,
          state.customerPersona.name,
        );
        if (pastContext) {
          augmentedPrompt += pastContext;
        }
      }

      let fullContent = "";
      let turnResult: SimulateTurnDone | null = null;

      const stream = simulateTurnStream(
        {
          persona: {
            name: activePersona.name,
            role: activePersona.role,
            system_prompt: augmentedPrompt,
          },
          conversation_history: history,
          session_context: get().turnCount === 0 ? state.topicSeed : undefined,
          max_tokens: 512,
        },
        abortController.signal,
      );

      for await (const event of stream) {
        // Check if aborted
        if (abortController.signal.aborted) return;

        if (event.type === "token") {
          fullContent += event.content;
          set({ streamingContent: fullContent });
        } else if (event.type === "done") {
          turnResult = event.data;
          fullContent = turnResult.content;
        } else if (event.type === "error") {
          _abortController = null;
          set({
            status: "error",
            lastApiError: `LLM error: ${event.error}`,
            streamingContent: "",
            streamingPersona: null,
          });
          return;
        }
      }

      // Finalize message
      const currentTurnCount = get().turnCount;
      const message: DynamicMessage = {
        id: `dyn-${Date.now()}-${currentTurnCount}`,
        role: activePersona.role,
        personaName: activePersona.name,
        personaAvatar: activePersona.avatar,
        personaColor: activePersona.color,
        content: fullContent,
        timestamp: new Date().toISOString(),
        turnId: turnResult?.turn_id,
        modelId: turnResult?.model_id,
        tokensUsed: turnResult?.tokens_used,
      };

      const updatedMessages = [...get().messages, message];
      const newTurnCount = get().turnCount + 1;

      _abortController = null;
      set({
        status: "ingesting",
        messages: updatedMessages,
        turnCount: newTurnCount,
        streamingContent: "",
        streamingPersona: null,
      });

      // Ingest into pipeline
      if (get().backendConnected) {
        try {
          const events = messageToEvents(
            {
              id: message.id,
              session_id: get().sessionId,
              role: activePersona.role === "customer" ? "user" : "agent",
              content: message.content,
              timestamp: message.timestamp,
              tools_used: undefined,
            },
            "fe-dynamic-sim",
          );
          const result = await getSharedClient().ingestBatch(events);
          set({
            ingestedEvents: (get().ingestedEvents || 0) + result.accepted,
          });

          // Wait for projection consumer
          await new Promise((r) => setTimeout(r, 200));

          // Fetch updated graph
          await fetchLiveGraph(
            get().sessionId,
            get().customerPersona!.name,
            "fe-dynamic-sim",
          );

          // Update pipeline stats
          const stats = await fetchPipelineStats();
          set({ pipelineStats: stats });
        } catch (err) {
          const errMsg = err instanceof EngramError ? err.message : String(err);
          set({ lastApiError: `Pipeline: ${errMsg}` });
        }
      }

      // Check termination
      if (newTurnCount >= get().maxTurns) {
        await get().endSession();
        return;
      }

      // Set waiting status for auto-play timer
      set({ status: get().isAutoPlaying ? "waiting" : "paused" });
    } catch (err) {
      if (_abortController?.signal.aborted) return;
      _abortController = null;
      const errMsg = err instanceof Error ? err.message : String(err);
      set({
        status: "error",
        lastApiError: `Generation error: ${errMsg}`,
        streamingContent: "",
        streamingPersona: null,
      });
    } finally {
      _generationLock = false;
    }
  },

  startAutoPlay: () => {
    const state = get();
    if (
      !state.customerPersona ||
      !state.supportPersona ||
      !state.backendConnected
    )
      return;
    set({ isAutoPlaying: true });
    if (
      state.status === "ready" ||
      state.status === "paused" ||
      state.status === "waiting"
    ) {
      set({ status: "waiting" });
    }
  },

  pauseAutoPlay: () => {
    set({ isAutoPlaying: false });
    const state = get();
    if (state.status === "waiting") {
      set({ status: "paused" });
    }
  },

  endSession: async () => {
    if (_abortController) _abortController.abort();
    _abortController = null;
    const state = get();

    set({
      status: "complete",
      isAutoPlaying: false,
      streamingContent: "",
      streamingPersona: null,
    });

    if (state.backendConnected && state.sessionId) {
      try {
        const endTime = new Date().toISOString();
        const endEvent: EventPayload = {
          event_id: crypto.randomUUID(),
          event_type: "system.session_end",
          occurred_at: endTime,
          session_id: state.sessionId,
          agent_id: "fe-dynamic-sim",
          trace_id: state._sessionTraceId,
          payload_ref: `inline://session-end-${state.sessionId}`,
          importance_hint: 2,
          status: "completed",
        };
        await getSharedClient().ingestBatch([endEvent]);

        // Wait for extraction consumer to process session_end
        await new Promise((r) => setTimeout(r, 500));

        // Re-fetch graph with Entity nodes from extraction
        await fetchLiveGraph(
          state.sessionId,
          state.customerPersona?.name ?? "",
          "fe-dynamic-sim",
        );

        // Fetch user data
        const userId = state.customerPersona?.id ?? "";
        if (userId) {
          await fetchLiveUserData(userId).catch(() => {});
        }

        const stats = await fetchPipelineStats();
        set({ pipelineStats: stats });
      } catch (err) {
        const errMsg = err instanceof EngramError ? err.message : String(err);
        set({ lastApiError: `End session error: ${errMsg}` });
      }
    }
  },

  setTurnDelay: (ms) => set({ turnDelayMs: ms }),
  setMaxTurns: (n) => set({ maxTurns: n }),

  clearContextGraph: async () => {
    const state = get();
    if (!state.backendConnected) return;
    set({ isClearing: true, lastApiError: null });
    try {
      await getSharedClient().replay();
      useGraphStore.getState().setGraphData([], []);
      clearUserStoreData();
      const stats = await fetchPipelineStats();
      set({
        isClearing: false,
        ingestedEvents: 0,
        pipelineStats: stats,
        lastApiError: null,
      });
    } catch (err) {
      const errMsg = err instanceof EngramError ? err.message : String(err);
      set({ isClearing: false, lastApiError: errMsg });
    }
  },

  triggerReconsolidate: async () => {
    const state = get();
    if (!state.backendConnected) return;
    set({ isReconsolidating: true, lastApiError: null });
    try {
      await getSharedClient().reconsolidate();
      await new Promise((r) => setTimeout(r, 500));
      if (state.sessionId) {
        await fetchLiveGraph(
          state.sessionId,
          state.customerPersona?.name ?? "",
          "fe-dynamic-sim",
        );
      }
      const stats = await fetchPipelineStats();
      set({
        isReconsolidating: false,
        pipelineStats: stats,
        lastApiError: null,
      });
    } catch (err) {
      const errMsg = err instanceof EngramError ? err.message : String(err);
      set({ isReconsolidating: false, lastApiError: errMsg });
    }
  },

  refreshPipelineStats: async () => {
    const stats = await fetchPipelineStats();
    set({ pipelineStats: stats });
    const state = get();
    if (state.sessionId && state.backendConnected) {
      await fetchLiveGraph(
        state.sessionId,
        state.customerPersona?.name ?? "",
        "fe-dynamic-sim",
      ).catch(() => {});
    }
  },

  reset: () => {
    _generationLock = false;
    get().enterPicker();
  },
}));
