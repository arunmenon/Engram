import { create } from 'zustand';
import { onRequest, onResponse } from '../api/client';
import { isLiveMode } from '../api/mode';
import { mockApiCalls } from '../data/mockApiCalls';

export interface ApiLogEntry {
  id: string;
  timestamp: string;
  method: string;
  url: string;
  status?: number;
  durationMs?: number;
  requestBody?: unknown;
  responseBody?: unknown;
}

function mockToLogEntries(): ApiLogEntry[] {
  return mockApiCalls.map((call) => ({
    id: call.id,
    timestamp: call.timestamp,
    method: call.method,
    url: call.endpoint,
    status: call.status,
    durationMs: call.latency_ms,
    requestBody: call.request,
    responseBody: call.response,
  }));
}

interface ApiLogState {
  calls: ApiLogEntry[];
  addCall: (call: ApiLogEntry) => void;
  clear: () => void;
}

export const useApiLogStore = create<ApiLogState>((set) => ({
  calls: isLiveMode() ? [] : mockToLogEntries(),

  addCall: (call) =>
    set((s) => ({ calls: [call, ...s.calls].slice(0, 100) })),
  clear: () => set({ calls: [] }),
}));

// Wire interceptors for live API calls
let callId = 0;
const pendingCalls = new Map<string, { entry: ApiLogEntry; timer: ReturnType<typeof setTimeout> }>();
const PENDING_TIMEOUT_MS = 30_000;

onRequest((url, method, body) => {
  const id = `call-${++callId}`;
  const entry: ApiLogEntry = {
    id,
    timestamp: new Date().toISOString(),
    method,
    url,
    requestBody: body,
  };
  const key = `${method}:${url}`;
  // Clean up any previous pending entry for this key
  const existing = pendingCalls.get(key);
  if (existing) clearTimeout(existing.timer);
  // Set timeout to prevent memory leaks from unmatched requests
  const timer = setTimeout(() => {
    pendingCalls.delete(key);
  }, PENDING_TIMEOUT_MS);
  pendingCalls.set(key, { entry, timer });
});

onResponse((url, method, status, body, durationMs) => {
  const key = `${method}:${url}`;
  const pendingRecord = pendingCalls.get(key);
  if (pendingRecord) {
    clearTimeout(pendingRecord.timer);
    pendingRecord.entry.status = status;
    pendingRecord.entry.durationMs = durationMs;
    pendingRecord.entry.responseBody = body;
    pendingCalls.delete(key);
    useApiLogStore.getState().addCall(pendingRecord.entry);
  } else {
    useApiLogStore.getState().addCall({
      id: `call-${++callId}`,
      timestamp: new Date().toISOString(),
      method,
      url,
      status,
      durationMs,
      responseBody: body,
    });
  }
});
