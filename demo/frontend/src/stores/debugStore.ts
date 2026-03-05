import { create } from 'zustand';
import type { StreamEvent, ConsumerGroupStatus, TimelinePoint, LatencyBucket } from '../data/mockDebug';
import {
  mockStreamEvents,
  mockConsumerGroups,
  mockNodeCounts,
  mockNodeCountTimeline,
  mockQueryLatencyHistogram,
} from '../data/mockDebug';

interface DebugState {
  streamEvents: StreamEvent[];
  consumerGroups: ConsumerGroupStatus[];
  nodeCountsByType: Record<string, number>;
  nodeCountTimeline: TimelinePoint[];
  queryLatencyHistogram: LatencyBucket[];
}

export const useDebugStore = create<DebugState>(() => ({
  streamEvents: mockStreamEvents,
  consumerGroups: mockConsumerGroups,
  nodeCountsByType: mockNodeCounts,
  nodeCountTimeline: mockNodeCountTimeline,
  queryLatencyHistogram: mockQueryLatencyHistogram,
}));
