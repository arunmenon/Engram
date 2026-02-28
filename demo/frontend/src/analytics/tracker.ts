import type { AnalyticsEvent } from './events';

class AnalyticsTracker {
  private sinks: Array<(event: AnalyticsEvent) => void> = [];

  addSink(sink: (event: AnalyticsEvent) => void) {
    this.sinks.push(sink);
  }

  track(event: AnalyticsEvent) {
    for (const sink of this.sinks) {
      try {
        sink(event);
      } catch {
        /* ignore sink errors */
      }
    }
  }
}

const consoleSink = (event: AnalyticsEvent) => {
  console.log('[analytics]', event.type, event);
};

export const tracker = new AnalyticsTracker();
tracker.addSink(consoleSink);
