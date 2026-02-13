import { Header } from './components/layout/Header';
import { ChatPanel } from './components/chat/ChatPanel';
import { GraphPanel } from './components/graph/GraphPanel';
import { InsightPanel } from './components/insight/InsightPanel';
import { SessionTimeline } from './components/timeline/SessionTimeline';

export default function App() {
  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <ChatPanel />
        <GraphPanel />
        <InsightPanel />
      </div>
      <SessionTimeline />
    </div>
  );
}
