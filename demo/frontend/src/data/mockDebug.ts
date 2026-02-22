export interface StreamEvent {
  global_position: string;
  event_type: string;
  session_id: string;
  timestamp: string;
  size_bytes: number;
}

export interface ConsumerGroupStatus {
  name: string;
  stream_group: string;
  pending: number;
  lag: number;
  last_delivered_id: string;
  consumers: number;
  status: 'healthy' | 'lagging' | 'idle';
}

export interface TimelinePoint {
  hour: string;
  Event: number;
  Entity: number;
  Summary: number;
  UserProfile: number;
  Preference: number;
  Skill: number;
  Workflow: number;
  BehavioralPattern: number;
}

export interface LatencyBucket {
  range: string;
  count: number;
  color: string;
}

function makeTimestamp(minutesAgo: number): string {
  const date = new Date('2024-03-22T09:14:00Z');
  date.setMinutes(date.getMinutes() - minutesAgo);
  return date.toISOString();
}

export const mockStreamEvents: StreamEvent[] = [
  { global_position: '1711094040000-0', event_type: 'agent.invoke', session_id: 'session-3', timestamp: makeTimestamp(0), size_bytes: 412 },
  { global_position: '1711094039000-0', event_type: 'tool.result', session_id: 'session-3', timestamp: makeTimestamp(1), size_bytes: 1284 },
  { global_position: '1711094038000-0', event_type: 'tool.execute', session_id: 'session-3', timestamp: makeTimestamp(2), size_bytes: 356 },
  { global_position: '1711094035000-0', event_type: 'agent.respond', session_id: 'session-3', timestamp: makeTimestamp(5), size_bytes: 892 },
  { global_position: '1711094030000-0', event_type: 'agent.invoke', session_id: 'session-3', timestamp: makeTimestamp(10), size_bytes: 428 },
  { global_position: '1711094025000-0', event_type: 'tool.execute', session_id: 'session-3', timestamp: makeTimestamp(15), size_bytes: 310 },
  { global_position: '1711094020000-0', event_type: 'tool.result', session_id: 'session-3', timestamp: makeTimestamp(20), size_bytes: 1560 },
  { global_position: '1711094015000-0', event_type: 'agent.respond', session_id: 'session-3', timestamp: makeTimestamp(25), size_bytes: 744 },
  { global_position: '1711094010000-0', event_type: 'system.session_end', session_id: 'session-2', timestamp: makeTimestamp(30), size_bytes: 128 },
  { global_position: '1711094005000-0', event_type: 'agent.respond', session_id: 'session-2', timestamp: makeTimestamp(35), size_bytes: 956 },
  { global_position: '1711094000000-0', event_type: 'tool.result', session_id: 'session-2', timestamp: makeTimestamp(40), size_bytes: 2048 },
  { global_position: '1711093995000-0', event_type: 'tool.execute', session_id: 'session-2', timestamp: makeTimestamp(45), size_bytes: 384 },
  { global_position: '1711093990000-0', event_type: 'agent.invoke', session_id: 'session-2', timestamp: makeTimestamp(50), size_bytes: 396 },
  { global_position: '1711093985000-0', event_type: 'agent.respond', session_id: 'session-2', timestamp: makeTimestamp(55), size_bytes: 1100 },
  { global_position: '1711093980000-0', event_type: 'tool.result', session_id: 'session-2', timestamp: makeTimestamp(60), size_bytes: 872 },
  { global_position: '1711093975000-0', event_type: 'tool.execute', session_id: 'session-2', timestamp: makeTimestamp(65), size_bytes: 290 },
  { global_position: '1711093970000-0', event_type: 'agent.invoke', session_id: 'session-2', timestamp: makeTimestamp(70), size_bytes: 440 },
  { global_position: '1711093960000-0', event_type: 'system.session_start', session_id: 'session-2', timestamp: makeTimestamp(80), size_bytes: 156 },
  { global_position: '1711093950000-0', event_type: 'system.session_end', session_id: 'session-1', timestamp: makeTimestamp(90), size_bytes: 132 },
  { global_position: '1711093940000-0', event_type: 'agent.respond', session_id: 'session-1', timestamp: makeTimestamp(100), size_bytes: 684 },
];

export const mockConsumerGroups: ConsumerGroupStatus[] = [
  { name: 'Graph Projection', stream_group: 'graph-projection', pending: 0, lag: 0, last_delivered_id: '1711094040000-0', consumers: 2, status: 'healthy' },
  { name: 'Session Extraction', stream_group: 'session-extraction', pending: 2, lag: 1, last_delivered_id: '1711094035000-0', consumers: 1, status: 'healthy' },
  { name: 'Enrichment', stream_group: 'enrichment', pending: 15, lag: 8, last_delivered_id: '1711094010000-0', consumers: 1, status: 'lagging' },
  { name: 'Consolidation', stream_group: 'consolidation', pending: 0, lag: 0, last_delivered_id: '1711093960000-0', consumers: 0, status: 'idle' },
];

export const mockNodeCounts: Record<string, number> = {
  Event: 42,
  Entity: 18,
  Summary: 6,
  UserProfile: 3,
  Preference: 8,
  Skill: 5,
  Workflow: 2,
  BehavioralPattern: 4,
};

function generateTimeline(): TimelinePoint[] {
  const points: TimelinePoint[] = [];
  const baseDate = new Date('2024-03-21T10:00:00Z');
  for (let i = 0; i < 24; i++) {
    const hour = new Date(baseDate);
    hour.setHours(hour.getHours() + i);
    const growth = 1 + i * 0.04;
    points.push({
      hour: hour.toISOString().slice(11, 16),
      Event: Math.round(18 + i * 1.0 * growth),
      Entity: Math.round(8 + i * 0.42 * growth),
      Summary: Math.round(2 + i * 0.17 * growth),
      UserProfile: Math.round(1 + i * 0.08),
      Preference: Math.round(3 + i * 0.21),
      Skill: Math.round(2 + i * 0.13),
      Workflow: Math.round(1 + i * 0.04),
      BehavioralPattern: Math.round(1 + i * 0.13),
    });
  }
  return points;
}

export const mockNodeCountTimeline: TimelinePoint[] = generateTimeline();

export const mockQueryLatencyHistogram: LatencyBucket[] = [
  { range: '0-10', count: 45, color: '#22c55e' },
  { range: '10-25', count: 82, color: '#4ade80' },
  { range: '25-50', count: 64, color: '#a3e635' },
  { range: '50-100', count: 38, color: '#facc15' },
  { range: '100-150', count: 22, color: '#fbbf24' },
  { range: '150-250', count: 14, color: '#f97316' },
  { range: '250-500', count: 8, color: '#ef4444' },
  { range: '500-1000', count: 3, color: '#dc2626' },
  { range: '1000-2000', count: 1, color: '#b91c1c' },
  { range: '2000+', count: 0, color: '#991b1b' },
];
