import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useDynamicSimStore } from '../../stores/dynamicSimStore';
import { useDynamicPlayback } from '../../hooks/useDynamicPlayback';
import { PersonaPicker } from './PersonaPicker';
import { DynamicControls } from './DynamicControls';
import { PipelineStatus } from './PipelineStatus';

export function DynamicChat() {
  const status = useDynamicSimStore(s => s.status);
  const messages = useDynamicSimStore(s => s.messages);
  const streamingContent = useDynamicSimStore(s => s.streamingContent);
  const streamingPersona = useDynamicSimStore(s => s.streamingPersona);
  const customerPersona = useDynamicSimStore(s => s.customerPersona);
  const supportPersona = useDynamicSimStore(s => s.supportPersona);
  const backendConnected = useDynamicSimStore(s => s.backendConnected);
  const pipelineStats = useDynamicSimStore(s => s.pipelineStats);
  const ingestedEvents = useDynamicSimStore(s => s.ingestedEvents);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Drive auto-play timer
  useDynamicPlayback();

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, streamingContent]);

  // Show picker
  if (status === 'picking') {
    return (
      <div className="w-[400px] shrink-0 bg-surface border-r border-muted-dark/30 flex flex-col">
        <PersonaPicker />
      </div>
    );
  }

  return (
    <div className="w-[400px] shrink-0 bg-surface border-r border-muted-dark/30 flex flex-col">
      {/* Persona header */}
      <div className="flex items-center gap-2 p-2 border-b border-muted-dark/30">
        {customerPersona && (
          <div className="flex items-center gap-1">
            <div
              className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white"
              style={{ backgroundColor: customerPersona.color }}
            >
              {customerPersona.avatar}
            </div>
            <span className="text-[10px] text-gray-300">{customerPersona.name}</span>
          </div>
        )}
        <span className="text-[10px] text-muted">vs</span>
        {supportPersona && (
          <div className="flex items-center gap-1">
            <div
              className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white"
              style={{ backgroundColor: supportPersona.color }}
            >
              {supportPersona.avatar}
            </div>
            <span className="text-[10px] text-gray-300">{supportPersona.name}</span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3" role="log" aria-live="polite">
        {messages.length === 0 && status === 'ready' && (
          <div className="flex-1 flex items-center justify-center h-full">
            <div className="text-center space-y-2 py-16">
              <div className="text-xs text-muted">Ready to begin</div>
              <div className="text-[10px] text-muted-dark">Press Play or Step to start the conversation</div>
            </div>
          </div>
        )}

        <AnimatePresence mode="popLayout">
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className={`flex gap-2 ${msg.role === 'support' ? 'flex-row-reverse' : ''}`}
            >
              <div
                className="w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-[8px] font-bold text-white"
                style={{ backgroundColor: msg.personaColor }}
              >
                {msg.personaAvatar}
              </div>
              <div
                className={`max-w-[80%] rounded-xl px-3 py-2 ${
                  msg.role === 'customer'
                    ? 'bg-surface-hover text-gray-200'
                    : 'bg-accent-blue/10 text-gray-200'
                }`}
                aria-label={`${msg.personaName}: ${msg.content}`}
              >
                <div className="text-[9px] font-semibold mb-0.5" style={{ color: msg.personaColor }}>
                  {msg.personaName}
                </div>
                <div className="text-xs leading-relaxed">{msg.content}</div>
                {msg.tokensUsed && (
                  <div className="text-[8px] text-muted mt-1">{msg.tokensUsed} tokens</div>
                )}
              </div>
            </motion.div>
          ))}

          {/* Streaming message */}
          {streamingContent && streamingPersona && (
            <motion.div
              key="streaming"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-2 ${streamingPersona.role === 'support' ? 'flex-row-reverse' : ''}`}
            >
              <div
                className="w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-[8px] font-bold text-white"
                style={{ backgroundColor: streamingPersona.color }}
              >
                {streamingPersona.avatar}
              </div>
              <div
                className={`max-w-[80%] rounded-xl px-3 py-2 ${
                  streamingPersona.role === 'customer'
                    ? 'bg-surface-hover text-gray-200'
                    : 'bg-accent-blue/10 text-gray-200'
                }`}
              >
                <div className="text-[9px] font-semibold mb-0.5" style={{ color: streamingPersona.color }}>
                  {streamingPersona.name}
                </div>
                <div className="text-xs leading-relaxed">
                  {streamingContent}
                  <span className="inline-block w-1.5 h-3 bg-accent-purple animate-pulse ml-0.5" />
                </div>
              </div>
            </motion.div>
          )}

          {/* Typing indicator (when generating but no content yet) */}
          {status === 'generating' && !streamingContent && streamingPersona && (
            <motion.div
              key="typing"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="flex items-center gap-1.5 px-3 py-2"
            >
              <div
                className="w-5 h-5 rounded-full shrink-0 flex items-center justify-center text-[8px] font-bold text-white"
                style={{ backgroundColor: streamingPersona.color }}
              >
                {streamingPersona.avatar}
              </div>
              <div className="text-[10px] text-muted italic">{streamingPersona.name} is typing</div>
              <div className="flex items-center gap-1">
                <motion.div className="w-1 h-1 rounded-full bg-muted" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0 }} />
                <motion.div className="w-1 h-1 rounded-full bg-muted" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }} />
                <motion.div className="w-1 h-1 rounded-full bg-muted" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Pipeline Status + Controls */}
      <PipelineStatus
        backendConnected={backendConnected}
        pipelineStats={pipelineStats}
        ingestedEvents={ingestedEvents}
      />
      <DynamicControls />
    </div>
  );
}
