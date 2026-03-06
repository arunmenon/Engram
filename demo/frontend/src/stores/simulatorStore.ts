import { create } from 'zustand';
import type { SimulatorScenario } from '../data/scenarios';
import { allScenarios } from '../data/scenarios';
import { useGraphStore } from './graphStore';
import {
  EngramError,
  messageToEvents,
  sessionLifecycleEvents,
  type EventPayload,
} from '../api/engram';
import { transformAtlasResponse } from '../api/transforms';
import {
  type PipelineStats,
  EMPTY_PIPELINE_STATS,
  getSharedClient,
  detectBackend,
  fetchPipelineStats,
  clearUserStoreData,
} from '../api/pipeline';

// Re-export PipelineStats for consumers that imported it from here
export type { PipelineStats };

export type SimulatorStatus = 'idle' | 'picking' | 'ready' | 'playing' | 'paused' | 'complete';

interface SimulatorState {
  status: SimulatorStatus;
  scenario: SimulatorScenario | null;
  currentStepIndex: number; // -1 = not started
  visibleMessagesPerSession: Record<string, number>;
  currentSessionId: string;
  isPlaying: boolean;
  playbackSpeed: number;

  /** Whether Engram backend is connected — NO local fallback */
  backendConnected: boolean;
  /** Whether detection is in progress */
  detecting: boolean;
  /** Cumulative ingested event count */
  ingestedEvents: number;
  /** Last Engram API error (for UI display) */
  lastApiError: string | null;
  /** Whether a clear operation is in progress */
  isClearing: boolean;
  /** Whether reconsolidation is in progress */
  isReconsolidating: boolean;
  /** Pipeline stats from backend */
  pipelineStats: PipelineStats;
  /** Sessions that have completed (session_end sent) */
  completedSessions: string[];

  // Actions
  enterPicker: () => void;
  pickScenario: (scenarioId: string) => void;
  play: () => void;
  pause: () => void;
  stepForward: () => void;
  stepBackward: () => void;
  goToStep: (index: number) => void;
  skipToStart: () => void;
  skipToEnd: () => void;
  setPlaybackSpeed: (speed: number) => void;
  reset: () => void;
  clearContextGraph: () => Promise<void>;
  triggerReconsolidate: () => Promise<void>;
  refreshPipelineStats: () => Promise<void>;
}

// ─── Engram Client (singleton from shared pipeline) ─────────────────────────

const engram = getSharedClient();

// ─── Track ingested session starts for cleanup ──────────────────────────────

const ingestedSessionIds = new Set<string>();

// ─── Engram Integration Layer (NO FALLBACKS) ────────────────────────────────

/**
 * Ingest events for a single message step into Engram.
 * Throws on failure — no silent degradation.
 */
async function ingestStepEvents(
  scenario: SimulatorScenario,
  stepIndex: number,
): Promise<{ accepted: number; sessionEnded: boolean }> {
  const msg = scenario.messages[stepIndex];
  if (!msg) throw new Error('Invalid step index');

  const events: EventPayload[] = [];
  const sessionId = msg.session_id;
  let sessionEnded = false;

  // If this is the first message in a session, send session_start first
  const isFirstInSession = stepIndex === 0 ||
    scenario.messages[stepIndex - 1]?.session_id !== sessionId;

  if (isFirstInSession && !ingestedSessionIds.has(sessionId)) {
    const session = scenario.sessions.find(s => s.id === sessionId);
    if (session) {
      const lifecycle = sessionLifecycleEvents(session);
      events.push(lifecycle.start);
      ingestedSessionIds.add(sessionId);
    }
  }

  // Convert the message to events
  const msgEvents = messageToEvents(msg);
  events.push(...msgEvents);

  // If this is the last message in a session, send session_end
  const isLastInSession = stepIndex === scenario.messages.length - 1 ||
    scenario.messages[stepIndex + 1]?.session_id !== sessionId;

  if (isLastInSession) {
    const session = scenario.sessions.find(s => s.id === sessionId);
    if (session) {
      const lifecycle = sessionLifecycleEvents(session);
      events.push(lifecycle.end);
      sessionEnded = true;
    }
  }

  // Batch ingest — let errors propagate
  const result = await engram.ingestBatch(events);
  return { accepted: result.accepted, sessionEnded };
}

/**
 * Fetch the live graph from Engram using querySubgraph (returns ALL node types)
 * for a comprehensive view, or getContext for session-scoped events.
 *
 * Note: simulatorStore's fetchLiveGraph takes a scenario to extract persona name,
 * unlike the shared pipeline version which takes a plain queryContext string.
 */
async function fetchLiveGraph(sessionId: string, scenario: SimulatorScenario): Promise<void> {
  // Use querySubgraph to get ALL node types (Events, Entities, Summaries, etc.)
  try {
    const atlas = await engram.querySubgraph({
      query: `session context for ${scenario.persona.name}`,
      session_id: sessionId,
      agent_id: 'fe-simulator',
      max_nodes: 200,
      max_depth: 5,
    });
    const { nodes, edges } = transformAtlasResponse(atlas);
    useGraphStore.getState().setGraphData(nodes, edges, atlas.meta);
    return;
  } catch {
    // querySubgraph may fail if no seed nodes found — fall back to getContext
  }

  // Fallback: getContext returns Event nodes for the session
  const atlas = await engram.getContext(sessionId, { maxNodes: 200, maxDepth: 5 });
  const { nodes, edges } = transformAtlasResponse(atlas);
  useGraphStore.getState().setGraphData(nodes, edges, atlas.meta);
}

/**
 * Fetch live user profile data from Engram.
 * Non-blocking — missing data is expected before extraction runs.
 *
 * Note: simulatorStore extracts userNodeId from atlas snapshots,
 * unlike the shared fetchLiveUserData which takes userId directly.
 */
async function fetchLiveUserData(scenario: SimulatorScenario): Promise<void> {
  const userNodeId = scenario.atlasSnapshots[scenario.atlasSnapshots.length - 1]
    ?.userProfile?.id;
  if (!userNodeId) return;

  const { fetchLiveUserData: sharedFetch } = await import('../api/pipeline');
  await sharedFetch(userNodeId);
}

// ─── Apply Step (Engram-only, no fallback) ──────────────────────────────────

/**
 * Ingest events for step, then fetch live graph. No local fallback.
 */
async function applyStep(
  scenario: SimulatorScenario,
  stepIndex: number,
  setState: (partial: Partial<SimulatorState>) => void,
) {
  try {
    // 1. Ingest events to real backend
    const { accepted, sessionEnded } = await ingestStepEvents(scenario, stepIndex);
    const newTotal = (useSimulatorStore.getState().ingestedEvents || 0) + accepted;
    setState({ ingestedEvents: newTotal, lastApiError: null });

    // 2. Wait for projection consumer to process
    await new Promise(r => setTimeout(r, 200));

    // 3. Fetch live graph from backend
    const msg = scenario.messages[stepIndex];
    await fetchLiveGraph(msg.session_id, scenario);

    // 4. If a session just ended, track it and trigger post-session pipeline
    if (sessionEnded) {
      const completed = [...useSimulatorStore.getState().completedSessions, msg.session_id];
      setState({ completedSessions: completed });

      // Wait a bit more for extraction consumer (Consumer 2) to process session_end
      await new Promise(r => setTimeout(r, 500));

      // Re-fetch graph — may now include Entity nodes from extraction
      await fetchLiveGraph(msg.session_id, scenario);

      // Fetch user data — extraction may have created UserProfile/Preferences
      await fetchLiveUserData(scenario).catch(() => {});
    }

    // 5. Fetch user data (non-blocking, may not exist yet)
    fetchLiveUserData(scenario).catch(() => {});

    // 6. Update pipeline stats
    const stats = await fetchPipelineStats();
    setState({ pipelineStats: stats });

  } catch (err) {
    const errMsg = err instanceof EngramError ? err.message : String(err);
    setState({ lastApiError: `Pipeline error: ${errMsg}` });
    console.error('[Simulator] Pipeline error:', err);
  }
}

/** Build visibleMessagesPerSession for messages[0..stepIndex] */
function buildVisibleCounts(scenario: SimulatorScenario, stepIndex: number): Record<string, number> {
  const counts: Record<string, number> = {};
  for (let i = 0; i <= stepIndex; i++) {
    const sid = scenario.messages[i].session_id;
    counts[sid] = (counts[sid] || 0) + 1;
  }
  return counts;
}

// ─── Store ──────────────────────────────────────────────────────────────────

export const useSimulatorStore = create<SimulatorState>((set, get) => ({
  status: 'picking',
  scenario: null,
  currentStepIndex: -1,
  visibleMessagesPerSession: {},
  currentSessionId: '',
  isPlaying: false,
  playbackSpeed: 1,
  backendConnected: false,
  detecting: true,
  ingestedEvents: 0,
  lastApiError: null,
  isClearing: false,
  isReconsolidating: false,
  pipelineStats: EMPTY_PIPELINE_STATS,
  completedSessions: [],

  enterPicker: () => {
    ingestedSessionIds.clear();
    set({
      status: 'picking',
      scenario: null,
      currentStepIndex: -1,
      visibleMessagesPerSession: {},
      currentSessionId: '',
      isPlaying: false,
      ingestedEvents: 0,
      lastApiError: null,
      pipelineStats: EMPTY_PIPELINE_STATS,
      completedSessions: [],
    });
    useGraphStore.getState().setGraphData([], []);
    clearUserStoreData();
  },

  pickScenario: (scenarioId: string) => {
    const scenario = allScenarios.find(s => s.id === scenarioId);
    if (!scenario) return;
    const firstSessionId = scenario.sessions[0]?.id ?? '';

    ingestedSessionIds.clear();

    set({
      status: 'ready',
      scenario,
      currentStepIndex: -1,
      visibleMessagesPerSession: {},
      currentSessionId: firstSessionId,
      isPlaying: false,
      detecting: true,
      backendConnected: false,
      ingestedEvents: 0,
      lastApiError: null,
      pipelineStats: EMPTY_PIPELINE_STATS,
      completedSessions: [],
    });
    useGraphStore.getState().setGraphData([], []);

    // Detect backend — REQUIRED, no local fallback
    detectBackend().then(async (available) => {
      if (available) {
        // Fetch initial pipeline stats
        const stats = await fetchPipelineStats();
        set({
          detecting: false,
          backendConnected: true,
          lastApiError: null,
          pipelineStats: stats,
        });
        console.log('[Simulator] Backend connected — Engram Live mode (no fallbacks)');
      } else {
        set({
          detecting: false,
          backendConnected: false,
          lastApiError: 'Engram backend not available. Start the backend with: docker compose -f docker/docker-compose.yml up -d',
        });
        console.error('[Simulator] Backend NOT available — cannot proceed without Engram');
      }
    });
  },

  play: () => {
    const state = get();
    if (!state.scenario || !state.backendConnected) {
      if (!state.backendConnected) {
        set({ lastApiError: 'Cannot play: Engram backend not connected' });
      }
      return;
    }
    const totalSteps = state.scenario.messages.length;

    if (state.currentStepIndex < 0) {
      // Start from beginning
      const msg = state.scenario.messages[0];
      if (!msg) return;
      const counts = buildVisibleCounts(state.scenario, 0);
      set({
        status: 'playing',
        isPlaying: true,
        currentStepIndex: 0,
        visibleMessagesPerSession: counts,
        currentSessionId: msg.session_id,
      });
      applyStep(state.scenario, 0, (p) => set(p as Partial<SimulatorState>));
      return;
    }

    if (state.currentStepIndex >= totalSteps - 1) {
      // Already at end — restart from beginning
      const msg = state.scenario.messages[0];
      if (!msg) return;
      const counts = buildVisibleCounts(state.scenario, 0);
      ingestedSessionIds.clear();
      set({
        status: 'playing',
        isPlaying: true,
        currentStepIndex: 0,
        visibleMessagesPerSession: counts,
        currentSessionId: msg.session_id,
        ingestedEvents: 0,
        completedSessions: [],
      });
      applyStep(state.scenario, 0, (p) => set(p as Partial<SimulatorState>));
      return;
    }

    // Resume
    set({ status: 'playing', isPlaying: true });
  },

  pause: () => set({ status: 'paused', isPlaying: false }),

  stepForward: () => {
    const state = get();
    if (!state.scenario || !state.backendConnected) return;
    const nextIndex = state.currentStepIndex + 1;
    if (nextIndex >= state.scenario.messages.length) {
      set({ status: 'complete', isPlaying: false });
      return;
    }
    const msg = state.scenario.messages[nextIndex];
    const counts = buildVisibleCounts(state.scenario, nextIndex);
    set({
      currentStepIndex: nextIndex,
      visibleMessagesPerSession: counts,
      currentSessionId: msg.session_id,
      status: nextIndex >= state.scenario.messages.length - 1 ? 'complete' : (state.isPlaying ? 'playing' : 'paused'),
      isPlaying: nextIndex >= state.scenario.messages.length - 1 ? false : state.isPlaying,
    });
    applyStep(state.scenario, nextIndex, (p) => set(p as Partial<SimulatorState>));
  },

  stepBackward: () => {
    const state = get();
    if (!state.scenario || !state.backendConnected) return;
    const prevIndex = state.currentStepIndex - 1;
    if (prevIndex < 0) return;
    const msg = state.scenario.messages[prevIndex];
    const counts = buildVisibleCounts(state.scenario, prevIndex);
    set({
      currentStepIndex: prevIndex,
      visibleMessagesPerSession: counts,
      currentSessionId: msg.session_id,
      status: 'paused',
      isPlaying: false,
    });
    // Re-fetch from backend — graph shows cumulative state (can't un-ingest)
    fetchLiveGraph(msg.session_id, state.scenario).catch((err) => {
      set({ lastApiError: `Fetch failed: ${err}` });
    });
    fetchLiveUserData(state.scenario).catch(() => {});
  },

  goToStep: (index: number) => {
    const state = get();
    if (!state.scenario || !state.backendConnected) return;
    const clamped = Math.max(0, Math.min(index, state.scenario.messages.length - 1));
    const msg = state.scenario.messages[clamped];
    if (!msg) return;
    const counts = buildVisibleCounts(state.scenario, clamped);
    set({
      currentStepIndex: clamped,
      visibleMessagesPerSession: counts,
      currentSessionId: msg.session_id,
      status: clamped >= state.scenario.messages.length - 1 ? 'complete' : 'paused',
      isPlaying: false,
    });
    // Re-fetch live graph (cumulative view from backend)
    fetchLiveGraph(msg.session_id, state.scenario).catch((err) => {
      set({ lastApiError: `Fetch failed: ${err}` });
    });
    fetchLiveUserData(state.scenario).catch(() => {});
  },

  skipToStart: () => {
    const state = get();
    if (!state.scenario) return;
    set({
      currentStepIndex: -1,
      visibleMessagesPerSession: {},
      currentSessionId: state.scenario.sessions[0]?.id ?? '',
      isPlaying: false,
      status: 'ready',
    });
    useGraphStore.getState().setGraphData([], []);
    clearUserStoreData();
  },

  skipToEnd: () => {
    const state = get();
    if (!state.scenario || !state.backendConnected) return;
    const lastIndex = state.scenario.messages.length - 1;
    const msg = state.scenario.messages[lastIndex];
    if (!msg) return;
    const counts = buildVisibleCounts(state.scenario, lastIndex);
    set({
      currentStepIndex: lastIndex,
      visibleMessagesPerSession: counts,
      currentSessionId: msg.session_id,
      isPlaying: false,
      status: 'complete',
    });

    // Ingest ALL events at once, then trigger full pipeline
    (async () => {
      try {
        // 1. Build all events for all sessions
        const allEvents: EventPayload[] = [];
        for (const session of state.scenario!.sessions) {
          const lc = sessionLifecycleEvents(session);
          allEvents.push(lc.start);
          const sessionMsgs = state.scenario!.messages.filter(m => m.session_id === session.id);
          for (const m of sessionMsgs) {
            allEvents.push(...messageToEvents(m));
          }
          allEvents.push(lc.end);
        }

        // 2. Batch ingest
        const result = await engram.ingestBatch(allEvents);
        set({
          ingestedEvents: result.accepted,
          lastApiError: null,
          completedSessions: state.scenario!.sessions.map(s => s.id),
        });

        // 3. Wait for projection + extraction consumers
        await new Promise(r => setTimeout(r, 800));

        // 4. Trigger reconsolidation to create Summary nodes
        try {
          await engram.reconsolidate();
          console.log('[Simulator] Reconsolidation triggered after skip-to-end');
        } catch (e) {
          console.warn('[Simulator] Reconsolidate failed (may need more events):', e);
        }

        // 5. Wait for consolidation
        await new Promise(r => setTimeout(r, 500));

        // 6. Fetch full graph + user data
        await fetchLiveGraph(msg.session_id, state.scenario!);
        await fetchLiveUserData(state.scenario!).catch(() => {});

        // 7. Update pipeline stats
        const stats = await fetchPipelineStats();
        set({ pipelineStats: stats });

      } catch (err) {
        const errMsg = err instanceof EngramError ? err.message : String(err);
        set({ lastApiError: `Skip-to-end pipeline error: ${errMsg}` });
        console.error('[Simulator] Skip-to-end failed:', err);
      }
    })();
  },

  setPlaybackSpeed: (speed: number) => set({ playbackSpeed: speed }),

  reset: () => {
    get().enterPicker();
  },

  clearContextGraph: async () => {
    const state = get();
    if (!state.backendConnected) {
      set({ lastApiError: 'Cannot clear: Engram backend not connected' });
      return;
    }

    set({ isClearing: true, lastApiError: null });
    try {
      await engram.replay();
      ingestedSessionIds.clear();

      // Clear local state
      useGraphStore.getState().setGraphData([], []);
      clearUserStoreData();

      // Fetch fresh stats
      const stats = await fetchPipelineStats();

      set({
        isClearing: false,
        ingestedEvents: 0,
        currentStepIndex: -1,
        visibleMessagesPerSession: {},
        status: state.scenario ? 'ready' : 'picking',
        isPlaying: false,
        lastApiError: null,
        pipelineStats: stats,
        completedSessions: [],
      });
      console.log('[Simulator] Context graph cleared via replay');
    } catch (err) {
      const errMsg = err instanceof EngramError ? err.message : 'Failed to clear context graph';
      set({ isClearing: false, lastApiError: errMsg });
      console.error('[Simulator] Clear failed:', err);
    }
  },

  triggerReconsolidate: async () => {
    const state = get();
    if (!state.backendConnected) {
      set({ lastApiError: 'Cannot reconsolidate: Engram backend not connected' });
      return;
    }

    set({ isReconsolidating: true, lastApiError: null });
    try {
      const result = await engram.reconsolidate();
      console.log('[Simulator] Reconsolidation result:', result);

      // Wait for Summary nodes to be written
      await new Promise(r => setTimeout(r, 500));

      // Re-fetch graph with Summary nodes
      if (state.scenario && state.currentSessionId) {
        await fetchLiveGraph(state.currentSessionId, state.scenario);
        await fetchLiveUserData(state.scenario).catch(() => {});
      }

      // Update stats
      const stats = await fetchPipelineStats();
      set({
        isReconsolidating: false,
        pipelineStats: stats,
        lastApiError: null,
      });
    } catch (err) {
      const errMsg = err instanceof EngramError ? err.message : 'Reconsolidation failed';
      set({ isReconsolidating: false, lastApiError: errMsg });
      console.error('[Simulator] Reconsolidate failed:', err);
    }
  },

  refreshPipelineStats: async () => {
    const stats = await fetchPipelineStats();
    set({ pipelineStats: stats });

    // Also re-fetch graph and user data
    const state = get();
    if (state.scenario && state.currentSessionId && state.backendConnected) {
      await fetchLiveGraph(state.currentSessionId, state.scenario).catch(() => {});
      await fetchLiveUserData(state.scenario).catch(() => {});
    }
  },
}));
