import { useEffect, useRef, useMemo } from 'react';
import { AnimatePresence } from 'framer-motion';
import { useSessionStore, selectCurrentMessages } from '../../stores/sessionStore';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';

export function ChatPanel() {
  const sessions = useSessionStore(s => s.sessions);
  const currentSessionId = useSessionStore(s => s.currentSessionId);
  const setCurrentSession = useSessionStore(s => s.setCurrentSession);
  const autoPlayStarted = useSessionStore(s => s.autoPlayStarted);
  const visibleMessagesPerSession = useSessionStore(s => s.visibleMessagesPerSession);
  const allCurrentMessages = useSessionStore(selectCurrentMessages);
  const scrollRef = useRef<HTMLDivElement>(null);

  const visibleMessages = useMemo(() => {
    if (!autoPlayStarted) return allCurrentMessages;
    const count = visibleMessagesPerSession[currentSessionId] || 0;
    return allCurrentMessages.slice(0, count);
  }, [autoPlayStarted, allCurrentMessages, visibleMessagesPerSession, currentSessionId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [currentSessionId, visibleMessages.length]);

  return (
    <div className="w-[400px] shrink-0 bg-surface border-r border-muted-dark/30 flex flex-col">
      {/* Session Tabs */}
      <div className="flex items-center gap-1 p-2 border-b border-muted-dark/30">
        {sessions.map((session, i) => (
          <button
            key={session.id}
            onClick={() => setCurrentSession(session.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              session.id === currentSessionId
                ? 'bg-surface-hover text-gray-100'
                : 'text-muted hover:text-muted-light hover:bg-surface-hover/50'
            }`}
          >
            <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: session.color }} />
            S{i + 1}
            <span className="text-[10px] text-muted hidden sm:inline">
              {session.title}
            </span>
          </button>
        ))}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        <AnimatePresence mode="popLayout">
          {visibleMessages.map(msg => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
        </AnimatePresence>
      </div>

      {/* Input */}
      <ChatInput />
    </div>
  );
}
