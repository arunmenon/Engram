/**
 * Engram TypeScript SDK — FE Shell client for the Context Graph API.
 *
 * Mirrors the Python SDK's `EngramClient` surface:
 *   ingest / ingestBatch / getContext / querySubgraph / getLineage
 *   getEntity / getUserProfile / getUserPreferences / getUserSkills
 *   getUserPatterns / getUserInterests / deleteUser / stats / health
 *
 * All calls go through the Vite proxy at `/v1/…` → localhost:8000.
 */

import type {
  AtlasResponse,
  AtlasNode,
  AtlasEdge,
  IntentType,
} from "../types/atlas";

// ─── SDK Types ──────────────────────────────────────────────────────────────

export interface EngramConfig {
  /** Base path for the API — defaults to '/v1' (Vite-proxied) */
  basePath?: string;
  /** Optional API key (sent as Bearer token) */
  apiKey?: string;
  /** Optional admin key for admin endpoints */
  adminKey?: string;
  /** Request timeout in ms (default 30000) */
  timeout?: number;
}

export interface IngestResult {
  event_id: string;
  global_position: string;
}

export interface BatchResult {
  accepted: number;
  rejected: number;
  results: IngestResult[];
  errors: Array<{
    index: number;
    event_id: string | null;
    errors: Array<{ field: string; message: string }>;
  }>;
}

export interface EventPayload {
  event_id: string;
  event_type: string;
  occurred_at: string;
  session_id: string;
  agent_id: string;
  trace_id: string;
  payload_ref: string;
  tool_name?: string;
  parent_event_id?: string;
  ended_at?: string;
  status?: "pending" | "running" | "completed" | "failed" | "timeout";
  schema_version?: number;
  importance_hint?: number;
  payload?: Record<string, unknown>;
}

export interface SubgraphQuery {
  query: string;
  session_id: string;
  agent_id?: string;
  max_nodes?: number;
  max_depth?: number;
  timeout_ms?: number;
  intent?: IntentType;
  seed_nodes?: string[];
}

export interface HealthStatus {
  status: string;
  redis: boolean;
  neo4j: boolean;
  version: string;
}

export interface StatsResponse {
  /** Node counts by label — key from admin endpoint is `nodes` */
  nodes: Record<string, number>;
  node_counts?: Record<string, number>;
  /** Edge counts by type — key from admin endpoint is `edges` */
  edges: Record<string, number>;
  edge_counts?: Record<string, number>;
  /** Redis stream info */
  redis?: { stream_length: number };
  stream_length?: number;
  total_nodes: number;
  total_edges: number;
}

export interface UserProfile {
  id: string;
  name: string;
  role: string;
  tech_level: string;
  communication_style: string;
  first_seen: string;
  last_seen: string;
  session_count: number;
  total_interactions: number;
  [key: string]: unknown;
}

export interface PreferenceNode {
  id: string;
  category: string;
  value: string;
  polarity: "positive" | "negative" | "neutral";
  confidence: number;
  source_event_ids: string[];
  last_updated: string;
  [key: string]: unknown;
}

export interface SkillNode {
  id: string;
  name: string;
  category: string;
  proficiency: number;
  source_event_ids: string[];
  [key: string]: unknown;
}

export interface BehavioralPatternNode {
  id: string;
  pattern_type: string;
  description: string;
  observation_count: number;
  confidence: number;
  [key: string]: unknown;
}

export interface InterestNode {
  entity_id: string;
  entity_name: string;
  weight: number;
  [key: string]: unknown;
}

export interface EntityResponse {
  id: string;
  entity_type: string;
  attributes: Record<string, unknown>;
  connected_events: string[];
  [key: string]: unknown;
}

export interface ReconsolidateResponse {
  sessions_processed: number;
  summaries_created: number;
  events_processed: number;
}

export interface PruneResponse {
  pruned_nodes: number;
  pruned_edges: number;
  dry_run: boolean;
  details?: Array<Record<string, unknown>>;
  truncated?: boolean;
}

export interface ReplayResponse {
  events_replayed: number;
  nodes_created: number;
  edges_created: number;
}

export interface FeedbackPayload {
  query_id: string;
  session_id: string;
  helpful_node_ids: string[];
  irrelevant_node_ids: string[];
  comment?: string;
}

// ─── Error Classes ──────────────────────────────────────────────────────────

export class EngramError extends Error {
  constructor(
    message: string,
    public status?: number,
    public body?: unknown,
  ) {
    super(message);
    this.name = "EngramError";
  }
}

export class AuthenticationError extends EngramError {
  constructor(message: string, body?: unknown) {
    super(message, 401, body);
    this.name = "AuthenticationError";
  }
}

export class NotFoundError extends EngramError {
  constructor(message: string, body?: unknown) {
    super(message, 404, body);
    this.name = "NotFoundError";
  }
}

export class ValidationError extends EngramError {
  constructor(message: string, body?: unknown) {
    super(message, 422, body);
    this.name = "ValidationError";
  }
}

export class RateLimitError extends EngramError {
  constructor(message: string, body?: unknown) {
    super(message, 429, body);
    this.name = "RateLimitError";
  }
}

export class ServerError extends EngramError {
  constructor(message: string, status: number, body?: unknown) {
    super(message, status, body);
    this.name = "ServerError";
  }
}

// ─── Client ─────────────────────────────────────────────────────────────────

export class EngramClient {
  private basePath: string;
  private apiKey?: string;
  private adminKey?: string;
  private timeout: number;

  // ── Interceptor hooks ─────────────────────────────────────────────────

  static requestHooks: Array<
    (url: string, method: string, body?: unknown) => void
  > = [];
  static responseHooks: Array<
    (
      url: string,
      method: string,
      status: number,
      body: unknown,
      durationMs: number,
    ) => void
  > = [];

  static onRequest(
    fn: (url: string, method: string, body?: unknown) => void,
  ): void {
    EngramClient.requestHooks.push(fn);
  }

  static onResponse(
    fn: (
      url: string,
      method: string,
      status: number,
      body: unknown,
      durationMs: number,
    ) => void,
  ): void {
    EngramClient.responseHooks.push(fn);
  }

  constructor(config: EngramConfig = {}) {
    this.basePath = config.basePath ?? "/v1";
    this.apiKey = config.apiKey;
    this.adminKey = config.adminKey;
    this.timeout = config.timeout ?? 30_000;
  }

  // ── Internal fetch ───────────────────────────────────────────────────────

  private async fetch<T>(
    path: string,
    options: {
      method?: string;
      body?: unknown;
      admin?: boolean;
      params?: Record<string, string | number | boolean | undefined>;
    } = {},
  ): Promise<T> {
    const { method = "GET", body, admin = false, params } = options;

    let url = `${this.basePath}${path}`;
    if (params) {
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined) qs.set(k, String(v));
      }
      const str = qs.toString();
      if (str) url += `?${str}`;
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    const key = admin ? this.adminKey : this.apiKey;
    if (key) headers["Authorization"] = `Bearer ${key}`;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    for (const hook of EngramClient.requestHooks) hook(url, method, body);
    const startTime = Date.now();

    try {
      const res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      clearTimeout(timer);

      let responseBody: unknown;
      try {
        responseBody = await res.json();
      } catch {
        responseBody = { error: `Non-JSON response (${res.status})` };
      }

      const durationMs = Date.now() - startTime;
      for (const hook of EngramClient.responseHooks)
        hook(url, method, res.status, responseBody, durationMs);

      if (!res.ok) {
        this.throwForStatus(res.status, `${method} ${url}`, responseBody);
      }

      return responseBody as T;
    } catch (err) {
      clearTimeout(timer);
      if (err instanceof EngramError) throw err;
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new EngramError(`Request timed out after ${this.timeout}ms`);
      }
      throw new EngramError(`Network error: ${(err as Error).message}`);
    }
  }

  private throwForStatus(
    status: number,
    context: string,
    body: unknown,
  ): never {
    const msg = `${context} failed (${status})`;
    if (status === 401) throw new AuthenticationError(msg, body);
    if (status === 404) throw new NotFoundError(msg, body);
    if (status === 422) throw new ValidationError(msg, body);
    if (status === 429) throw new RateLimitError(msg, body);
    if (status >= 500) throw new ServerError(msg, status, body);
    throw new EngramError(msg, status, body);
  }

  // ── Event Ingestion ──────────────────────────────────────────────────────

  /** Ingest a single event */
  async ingest(event: EventPayload): Promise<IngestResult> {
    return this.fetch<IngestResult>("/events", {
      method: "POST",
      body: event,
    });
  }

  /** Ingest a batch of events (up to 1000) */
  async ingestBatch(events: EventPayload[]): Promise<BatchResult> {
    return this.fetch<BatchResult>("/events/batch", {
      method: "POST",
      body: { events },
    });
  }

  // ── Context & Query ──────────────────────────────────────────────────────

  /** Retrieve session working memory (Atlas response) */
  async getContext(
    sessionId: string,
    options?: {
      maxNodes?: number;
      maxDepth?: number;
      query?: string;
      cursor?: string;
    },
  ): Promise<AtlasResponse> {
    return this.fetch<AtlasResponse>(`/context/${sessionId}`, {
      params: {
        max_nodes: options?.maxNodes,
        max_depth: options?.maxDepth,
        query: options?.query,
        cursor: options?.cursor,
      },
    });
  }

  /** Intent-aware subgraph query */
  async querySubgraph(query: SubgraphQuery): Promise<AtlasResponse> {
    return this.fetch<AtlasResponse>("/query/subgraph", {
      method: "POST",
      body: query,
    });
  }

  /** Traverse causal chains from a node */
  async getLineage(
    nodeId: string,
    options?: {
      maxDepth?: number;
      maxNodes?: number;
      intent?: IntentType;
      cursor?: string;
    },
  ): Promise<AtlasResponse> {
    return this.fetch<AtlasResponse>(`/nodes/${nodeId}/lineage`, {
      params: {
        max_depth: options?.maxDepth,
        max_nodes: options?.maxNodes,
        intent: options?.intent,
        cursor: options?.cursor,
      },
    });
  }

  // ── Entities ─────────────────────────────────────────────────────────────

  /** Retrieve an entity and its connected events */
  async getEntity(entityId: string): Promise<EntityResponse> {
    return this.fetch<EntityResponse>(`/entities/${entityId}`);
  }

  // ── User Endpoints (admin) ───────────────────────────────────────────────

  async getUserProfile(userId: string): Promise<UserProfile> {
    return this.fetch<UserProfile>(`/users/${userId}/profile`, { admin: true });
  }

  async getUserPreferences(
    userId: string,
    category?: string,
  ): Promise<PreferenceNode[]> {
    return this.fetch<PreferenceNode[]>(`/users/${userId}/preferences`, {
      admin: true,
      params: category ? { category } : undefined,
    });
  }

  async getUserSkills(userId: string): Promise<SkillNode[]> {
    return this.fetch<SkillNode[]>(`/users/${userId}/skills`, { admin: true });
  }

  async getUserPatterns(userId: string): Promise<BehavioralPatternNode[]> {
    return this.fetch<BehavioralPatternNode[]>(`/users/${userId}/patterns`, {
      admin: true,
    });
  }

  async getUserInterests(userId: string): Promise<InterestNode[]> {
    return this.fetch<InterestNode[]>(`/users/${userId}/interests`, {
      admin: true,
    });
  }

  /** GDPR data export */
  async exportUserData(userId: string): Promise<unknown> {
    return this.fetch(`/users/${userId}/data-export`, { admin: true });
  }

  /** GDPR cascade erasure — deletes all user data */
  async deleteUser(userId: string): Promise<unknown> {
    return this.fetch(`/users/${userId}`, { method: "DELETE", admin: true });
  }

  // ── Feedback ─────────────────────────────────────────────────────────────

  /** Submit retrieval quality feedback */
  async submitFeedback(
    feedback: FeedbackPayload,
  ): Promise<{ global_position: string }> {
    return this.fetch("/feedback", { method: "POST", body: feedback });
  }

  // ── Health & Admin ───────────────────────────────────────────────────────

  /** Basic health check (no auth required) */
  async health(): Promise<HealthStatus> {
    return this.fetch<HealthStatus>("/health");
  }

  /** Detailed health check */
  async healthDetailed(): Promise<unknown> {
    return this.fetch("/admin/health/detailed", { admin: true });
  }

  /** Graph and stream statistics */
  async stats(): Promise<StatsResponse> {
    return this.fetch<StatsResponse>("/admin/stats", { admin: true });
  }

  /** Trigger re-consolidation */
  async reconsolidate(sessionId?: string): Promise<ReconsolidateResponse> {
    return this.fetch<ReconsolidateResponse>("/admin/reconsolidate", {
      method: "POST",
      body: { session_id: sessionId ?? null },
      admin: true,
    });
  }

  /** Retention-based pruning */
  async prune(tier: "warm" | "cold", dryRun = true): Promise<PruneResponse> {
    return this.fetch<PruneResponse>("/admin/prune", {
      method: "POST",
      body: { tier, dry_run: dryRun },
      admin: true,
    });
  }

  /** Rebuild Neo4j from Redis (destructive) */
  async replay(): Promise<ReplayResponse> {
    return this.fetch<ReplayResponse>("/admin/replay", {
      method: "POST",
      body: { confirm: true },
      admin: true,
    });
  }
}

// ─── Singleton ──────────────────────────────────────────────────────────────

let _defaultClient: EngramClient | null = null;

/** Get or create the default Engram client (singleton) */
export function getEngramClient(config?: EngramConfig): EngramClient {
  if (!_defaultClient || config) {
    _defaultClient = new EngramClient(config);
  }
  return _defaultClient;
}

// ─── Session Helper ─────────────────────────────────────────────────────────

/**
 * Create an event payload with auto-generated IDs.
 * Mirrors the Python SDK's `SessionManager.record()` convenience.
 */
export function createEvent(opts: {
  sessionId: string;
  agentId?: string;
  traceId?: string;
  eventType?: string;
  content?: string;
  toolName?: string;
  parentEventId?: string;
  importanceHint?: number;
  status?: EventPayload["status"];
}): EventPayload {
  return {
    event_id: crypto.randomUUID(),
    event_type: opts.eventType ?? "observation.input",
    occurred_at: new Date().toISOString(),
    session_id: opts.sessionId,
    agent_id: opts.agentId ?? "fe-simulator",
    trace_id: opts.traceId ?? crypto.randomUUID(),
    payload_ref: `inline://${crypto.randomUUID()}`,
    tool_name: opts.toolName,
    parent_event_id: opts.parentEventId,
    importance_hint: opts.importanceHint,
    status: opts.status ?? "completed",
  };
}

// ─── Timestamp Rebasing ─────────────────────────────────────────────────────

/**
 * Rebase a timestamp from its original base time to a new base time.
 * Used to shift scenario timestamps (e.g. 2024 dates) to current time.
 *
 * @param originalTimestamp - ISO timestamp from the scenario data
 * @param originalBaseTime - ISO timestamp representing the scenario's start time
 * @param newBaseTime - ISO timestamp representing "now" (the new start time)
 * @returns ISO string with the rebased timestamp
 */
export function rebaseTimestamp(
  originalTimestamp: string,
  originalBaseTime: string,
  newBaseTime: string,
): string {
  const offsetMs =
    new Date(originalTimestamp).getTime() -
    new Date(originalBaseTime).getTime();
  return new Date(new Date(newBaseTime).getTime() + offsetMs).toISOString();
}

// ─── Simulator-specific helpers ─────────────────────────────────────────────

/**
 * Convert a simulator chat message + graph node into an EventPayload
 * suitable for ingestion into the real Engram backend.
 */
export function messageToEvents(
  message: {
    id: string;
    session_id: string;
    role: "user" | "agent";
    content: string;
    timestamp: string;
    tools_used?: string[];
  },
  agentId = "fe-simulator",
  traceId?: string,
): EventPayload[] {
  const trace = traceId ?? crypto.randomUUID();
  const events: EventPayload[] = [];

  // Main message event
  events.push({
    event_id: crypto.randomUUID(),
    event_type: message.role === "user" ? "observation.input" : "agent.invoke",
    occurred_at: message.timestamp,
    session_id: message.session_id,
    agent_id: agentId,
    trace_id: trace,
    payload_ref: `inline://${message.id}`,
    importance_hint: message.role === "user" ? 6 : 5,
    status: "completed",
    payload: { content: message.content, role: message.role },
  });

  // Tool execution events
  if (message.tools_used) {
    for (const tool of message.tools_used) {
      events.push({
        event_id: crypto.randomUUID(),
        event_type: "tool.execute",
        occurred_at: message.timestamp,
        session_id: message.session_id,
        agent_id: agentId,
        trace_id: trace,
        payload_ref: `inline://tool-${tool}-${message.id}`,
        tool_name: tool,
        parent_event_id: events[0].event_id,
        importance_hint: 5,
        status: "completed",
        payload: { content: message.content, role: message.role },
      });
    }
  }

  return events;
}

// ─── Dynamic Simulation Types ───────────────────────────────────────────────

export interface PersonaSpec {
  name: string;
  role: "customer" | "support";
  system_prompt: string;
  model_id?: string;
  temperature?: number;
}

export interface SimulateTurnRequest {
  persona: PersonaSpec;
  conversation_history: Array<{ role: string; content: string }>;
  session_context?: string;
  max_tokens?: number;
  stream?: boolean;
}

export interface SimulateTurnDone {
  content: string;
  turn_id: string;
  model_id: string;
  tokens_used: number;
}

export type SimulateEvent =
  | { type: "token"; content: string; index: number }
  | { type: "done"; data: SimulateTurnDone }
  | { type: "error"; error: string };

/**
 * Stream a simulated conversation turn via SSE.
 * Uses native fetch + ReadableStream — no extra npm deps.
 */
export async function* simulateTurnStream(
  request: SimulateTurnRequest,
  signal?: AbortSignal,
  apiKey?: string,
): AsyncGenerator<SimulateEvent> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

  const response = await fetch("/v1/simulate/turn", {
    method: "POST",
    headers,
    body: JSON.stringify({ ...request, stream: true }),
    signal,
  });

  if (!response.ok) {
    const body = await response.text();
    yield { type: "error", error: `HTTP ${response.status}: ${body}` };
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    yield { type: "error", error: "No response body" };
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      let currentEvent = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const data = line.slice(6);
          try {
            const parsed = JSON.parse(data);
            if (currentEvent === "token") {
              yield {
                type: "token",
                content: parsed.content,
                index: parsed.index,
              };
            } else if (currentEvent === "done") {
              yield { type: "done", data: parsed as SimulateTurnDone };
            } else if (currentEvent === "error") {
              yield { type: "error", error: parsed.error ?? "Unknown error" };
            }
          } catch {
            // Skip malformed JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Build session lifecycle events (start + end) for a session.
 */
export function sessionLifecycleEvents(
  session: { id: string; start_time: string; end_time: string },
  agentId = "fe-simulator",
): { start: EventPayload; end: EventPayload } {
  const trace = crypto.randomUUID();
  const startEvent: EventPayload = {
    event_id: crypto.randomUUID(),
    event_type: "system.session_start",
    occurred_at: session.start_time,
    session_id: session.id,
    agent_id: agentId,
    trace_id: trace,
    payload_ref: `inline://session-start-${session.id}`,
    importance_hint: 3,
    status: "completed",
    payload: { session_id: session.id },
  };
  const endEvent: EventPayload = {
    event_id: crypto.randomUUID(),
    event_type: "system.session_end",
    occurred_at: session.end_time,
    session_id: session.id,
    agent_id: agentId,
    trace_id: trace,
    payload_ref: `inline://session-end-${session.id}`,
    parent_event_id: startEvent.event_id,
    importance_hint: 2,
    status: "completed",
    payload: { session_id: session.id },
  };
  return { start: startEvent, end: endEvent };
}
