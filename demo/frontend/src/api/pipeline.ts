/**
 * Shared pipeline utilities used by both simulator and dynamic stores.
 */
import { EngramClient, type StatsResponse } from "./engram";
import { transformAtlasResponse } from "./transforms";
import { useGraphStore } from "../stores/graphStore";
import { useUserStore } from "../stores/userStore";
import { useApiLogStore } from "../stores/apiLogStore";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface PipelineStats {
  nodeCounts: Record<string, number>;
  edgeCounts: Record<string, number>;
  streamLength: number;
  totalNodes: number;
  totalEdges: number;
  fetchedAt: string | null;
}

export const EMPTY_PIPELINE_STATS: PipelineStats = {
  nodeCounts: {},
  edgeCounts: {},
  streamLength: 0,
  totalNodes: 0,
  totalEdges: 0,
  fetchedAt: null,
};

// ─── Shared Engram Client ───────────────────────────────────────────────────

const engram = new EngramClient();

export function getSharedClient(): EngramClient {
  return engram;
}

// ─── Bridge EngramClient hooks to apiLogStore ───────────────────────────────

let _interceptorCallId = 0;
const _pendingCalls = new Map<
  string,
  {
    entry: {
      id: string;
      timestamp: string;
      method: string;
      url: string;
      requestBody?: unknown;
    };
    timer: ReturnType<typeof setTimeout>;
  }
>();

EngramClient.onRequest((url, method, body) => {
  const id = `engram-${++_interceptorCallId}`;
  const key = `${method}:${url}`;
  const existing = _pendingCalls.get(key);
  if (existing) clearTimeout(existing.timer);
  const timer = setTimeout(() => _pendingCalls.delete(key), 30_000);
  _pendingCalls.set(key, {
    entry: {
      id,
      timestamp: new Date().toISOString(),
      method,
      url,
      requestBody: body,
    },
    timer,
  });
});

EngramClient.onResponse((url, method, status, body, durationMs) => {
  const key = `${method}:${url}`;
  const pending = _pendingCalls.get(key);
  if (pending) {
    clearTimeout(pending.timer);
    _pendingCalls.delete(key);
    useApiLogStore.getState().addCall({
      ...pending.entry,
      status,
      durationMs,
      responseBody: body,
    });
  } else {
    useApiLogStore.getState().addCall({
      id: `engram-${++_interceptorCallId}`,
      timestamp: new Date().toISOString(),
      method,
      url,
      status,
      durationMs,
      responseBody: body,
    });
  }
});

// ─── Shared Functions ───────────────────────────────────────────────────────

export async function detectBackend(): Promise<boolean> {
  try {
    const h = await engram.health();
    return h.status === "ok" || h.status === "healthy";
  } catch (err) {
    console.warn("[Pipeline] detectBackend failed:", err);
    return false;
  }
}

export async function fetchPipelineStats(): Promise<PipelineStats> {
  try {
    const raw: StatsResponse = await engram.stats();
    return {
      nodeCounts: raw.nodes ?? raw.node_counts ?? {},
      edgeCounts: raw.edges ?? raw.edge_counts ?? {},
      streamLength: raw.redis?.stream_length ?? raw.stream_length ?? 0,
      totalNodes: raw.total_nodes ?? 0,
      totalEdges: raw.total_edges ?? 0,
      fetchedAt: new Date().toISOString(),
    };
  } catch (err) {
    console.warn("[Pipeline] fetchPipelineStats failed:", err);
    return EMPTY_PIPELINE_STATS;
  }
}

export async function fetchLiveGraph(
  sessionId: string,
  queryContext: string,
  agentId = "fe-simulator",
): Promise<void> {
  try {
    const atlas = await engram.querySubgraph({
      query: `session context for ${queryContext}`,
      session_id: sessionId,
      agent_id: agentId,
      max_nodes: 200,
      max_depth: 5,
    });
    const { nodes, edges } = transformAtlasResponse(atlas);
    useGraphStore.getState().setGraphData(nodes, edges, atlas.meta);
    return;
  } catch (err) {
    console.warn(
      "[Pipeline] querySubgraph failed, falling back to getContext",
      err,
    );
  }
  try {
    const atlas = await engram.getContext(sessionId, {
      maxNodes: 200,
      maxDepth: 5,
    });
    const { nodes, edges } = transformAtlasResponse(atlas);
    useGraphStore.getState().setGraphData(nodes, edges, atlas.meta);
  } catch (err) {
    console.warn("[Pipeline] getContext failed, graph not available yet", err);
  }
}

export async function fetchLiveUserData(userId: string): Promise<void> {
  const [profile, preferences, skills, interests, patterns] =
    await Promise.allSettled([
      engram.getUserProfile(userId),
      engram.getUserPreferences(userId),
      engram.getUserSkills(userId),
      engram.getUserPatterns(userId),
      engram.getUserInterests(userId),
    ]);

  const u = useUserStore.getState();
  if (profile.status === "fulfilled") u.setProfile(profile.value);
  if (preferences.status === "fulfilled")
    u.setPreferences(
      preferences.value as Parameters<typeof u.setPreferences>[0],
    );
  if (skills.status === "fulfilled")
    u.setSkills(skills.value as Parameters<typeof u.setSkills>[0]);
  // API types (InterestNode/BehavioralPatternNode) differ from store types (UserInterest/EnhancedPattern)
  // but are structurally compatible at runtime via [key: string]: unknown index signatures
  if (interests.status === "fulfilled")
    u.setInterests(
      interests.value as unknown as Parameters<typeof u.setInterests>[0],
    );
  if (patterns.status === "fulfilled")
    u.setPatterns(
      patterns.value as unknown as Parameters<typeof u.setPatterns>[0],
    );
}

export function clearUserStoreData(): void {
  const u = useUserStore.getState();
  u.setProfile(null);
  u.setPreferences([]);
  u.setSkills([]);
  u.setInterests([]);
  u.setPatterns([]);
}
