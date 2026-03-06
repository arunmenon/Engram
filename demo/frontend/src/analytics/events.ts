export type AnalyticsEvent =
  | { type: 'node.click'; nodeId: string; nodeType: string }
  | { type: 'node.hover'; nodeId: string; nodeType: string; durationMs: number }
  | { type: 'playback.play' }
  | { type: 'playback.pause' }
  | { type: 'playback.step'; direction: 'forward' | 'backward'; stepIndex: number }
  | { type: 'playback.speed_change'; speed: number }
  | { type: 'session.switch'; sessionId: string }
  | { type: 'insight_tab.switch'; tab: string }
  | { type: 'filter.toggle'; filterType: 'node' | 'edge'; value: string; enabled: boolean }
  | { type: 'graph.layout_change'; layout: string }
  | { type: 'graph.export_png' }
  | { type: 'graph.copy_link' };
