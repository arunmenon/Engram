import { useEffect } from "react";
import { Header } from "./components/layout/Header";
import { ChatPanel } from "./components/chat/ChatPanel";
import { GraphPanel } from "./components/graph/GraphPanel";
import { InsightPanel } from "./components/insight/InsightPanel";
import { SessionTimeline } from "./components/timeline/SessionTimeline";
import { ScreenReaderAnnouncer } from "./components/shared/ScreenReaderAnnouncer";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { useKeyboardNavigation } from "./hooks/useKeyboardNavigation";
import { usePlaybackUrl } from "./hooks/usePlaybackUrl";
import { useInsightStore } from "./stores/insightStore";

export default function App() {
  useKeyboardNavigation();
  usePlaybackUrl();

  useEffect(() => {
    const handleDebugToggle = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === "D") {
        e.preventDefault();
        useInsightStore.getState().toggleDebug();
      }
    };
    window.addEventListener("keydown", handleDebugToggle);
    return () => window.removeEventListener("keydown", handleDebugToggle);
  }, []);

  return (
    <ErrorBoundary>
      <div className="h-screen w-screen flex flex-col overflow-hidden">
        <ScreenReaderAnnouncer />
        <Header />
        <div className="flex flex-1 overflow-hidden">
          <div
            role="region"
            aria-label="Chat conversation"
            className="contents"
          >
            <ErrorBoundary>
              <ChatPanel />
            </ErrorBoundary>
          </div>
          <div
            role="region"
            aria-label="Knowledge graph visualization"
            className="contents"
          >
            <ErrorBoundary>
              <GraphPanel />
            </ErrorBoundary>
          </div>
          <div role="region" aria-label="Context insights" className="contents">
            <ErrorBoundary>
              <InsightPanel />
            </ErrorBoundary>
          </div>
        </div>
        <div role="region" aria-label="Session timeline">
          <SessionTimeline />
        </div>
      </div>
    </ErrorBoundary>
  );
}
