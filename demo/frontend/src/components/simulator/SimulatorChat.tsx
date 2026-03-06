import { useEffect, useRef, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useSimulatorStore } from '../../stores/simulatorStore';
import { ChatMessage } from '../chat/ChatMessage';
import { SimulatorControls } from './SimulatorControls';
import { SimulatorPicker } from './SimulatorPicker';
import { PipelineStatus } from './PipelineStatus';

function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className="flex items-center gap-1.5 px-3 py-2"
    >
      <div className="flex items-center gap-1 bg-surface-hover rounded-xl px-3 py-2">
        <motion.div
          className="w-1.5 h-1.5 rounded-full bg-muted"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
        />
        <motion.div
          className="w-1.5 h-1.5 rounded-full bg-muted"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
        />
        <motion.div
          className="w-1.5 h-1.5 rounded-full bg-muted"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
        />
      </div>
    </motion.div>
  );
}

export function SimulatorChat() {
  const status = useSimulatorStore(s => s.status);
  const scenario = useSimulatorStore(s => s.scenario);
  const currentSessionId = useSimulatorStore(s => s.currentSessionId);
  const visibleMessagesPerSession = useSimulatorStore(s => s.visibleMessagesPerSession);
  const currentStepIndex = useSimulatorStore(s => s.currentStepIndex);
  const isPlaying = useSimulatorStore(s => s.isPlaying);

  const scrollRef = useRef<HTMLDivElement>(null);

  // All hooks must be called before any conditional returns
  const currentMessages = useMemo(() => {
    if (!scenario) return [];
    const allForSession = scenario.messages.filter(m => m.session_id === currentSessionId);
    const count = visibleMessagesPerSession[currentSessionId] || 0;
    return allForSession.slice(0, count);
  }, [scenario, currentSessionId, visibleMessagesPerSession]);

  const showTyping = useMemo(() => {
    if (!scenario || !isPlaying || currentStepIndex < 0) return false;
    const nextIndex = currentStepIndex + 1;
    if (nextIndex >= scenario.messages.length) return false;
    const nextMsg = scenario.messages[nextIndex];
    return nextMsg.session_id === currentSessionId;
  }, [scenario, isPlaying, currentStepIndex, currentSessionId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [currentMessages.length, currentSessionId]);

  // Show picker when in picking state
  if (status === 'picking' || !scenario) {
    return (
      <div className="w-[400px] shrink-0 bg-surface border-r border-muted-dark/30 flex flex-col">
        <SimulatorPicker />
      </div>
    );
  }

  const handleSessionTabClick = (sessionId: string) => {
    if (sessionId === currentSessionId) return;
    const firstMsgIdx = scenario.messages.findIndex(m => m.session_id === sessionId);
    if (firstMsgIdx >= 0 && firstMsgIdx <= currentStepIndex) {
      useSimulatorStore.setState({ currentSessionId: sessionId });
    }
  };

  const visibleSessions = scenario.sessions.filter(session => {
    return (visibleMessagesPerSession[session.id] || 0) > 0;
  });

  return (
    <div className="w-[400px] shrink-0 bg-surface border-r border-muted-dark/30 flex flex-col">
      {/* Session Tabs */}
      <div className="flex items-center gap-1 p-2 border-b border-muted-dark/30">
        {scenario.sessions.map((session, i) => {
          const isVisible = visibleSessions.includes(session);
          const isActive = session.id === currentSessionId;
          if (!isVisible && !isActive) {
            return (
              <div
                key={session.id}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-dark/50"
              >
                <div className="w-2 h-2 rounded-full bg-muted-dark/20" />
                S{i + 1}
              </div>
            );
          }
          return (
            <button
              key={session.id}
              onClick={() => handleSessionTabClick(session.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-surface-hover text-gray-100'
                  : 'text-muted hover:text-muted-light hover:bg-surface-hover/50'
              }`}
            >
              <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: session.color }} />
              S{i + 1}
              <span className="text-[10px] text-muted hidden sm:inline truncate max-w-[100px]">
                {session.title}
              </span>
            </button>
          );
        })}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {currentStepIndex < 0 ? (
          <div className="flex-1 flex items-center justify-center h-full">
            <div className="text-center space-y-2 py-16">
              <div className="text-xs text-muted">Ready to begin</div>
              <div className="text-[10px] text-muted-dark">Press Play or Step Forward to start</div>
            </div>
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            {currentMessages.map(msg => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              >
                <ChatMessage message={msg} />
              </motion.div>
            ))}
            {showTyping && <TypingIndicator key="typing" />}
          </AnimatePresence>
        )}
      </div>

      {/* Pipeline Status + Simulator Controls */}
      <PipelineStatus
        backendConnected={useSimulatorStore(s => s.backendConnected)}
        pipelineStats={useSimulatorStore(s => s.pipelineStats)}
        ingestedEvents={useSimulatorStore(s => s.ingestedEvents)}
      />
      <SimulatorControls />
    </div>
  );
}
