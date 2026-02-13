import { forwardRef } from 'react';
import { motion } from 'framer-motion';
import { ProvenanceBadge } from '../shared/ProvenanceBadge';
import { ContextUsed } from './ContextUsed';
import type { ChatMessage as ChatMessageType } from '../../types/chat';

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(function ChatMessage({ message }, ref) {
  const isUser = message.role === 'user';
  const time = new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`max-w-[85%] ${isUser ? 'order-1' : 'order-0'}`}>
        <div
          className={`px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? 'bg-accent-blue text-white'
              : 'bg-surface-card border border-muted-dark/30 text-gray-200'
          }`}
        >
          {message.content}
        </div>

        {!isUser && (
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5 px-1">
            {message.tools_used?.map(tool => (
              <span
                key={tool}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-accent-green/15 text-accent-green"
              >
                {tool}
              </span>
            ))}

            {message.provenance_node_ids && message.provenance_node_ids.length > 0 && (
              <ProvenanceBadge
                nodeIds={message.provenance_node_ids}
                count={message.provenance_node_ids.length}
              />
            )}
          </div>
        )}

        {!isUser && message.context_nodes_used && message.context_nodes_used > 0 && message.provenance_node_ids && (
          <ContextUsed
            nodeIds={message.provenance_node_ids}
            count={message.context_nodes_used}
          />
        )}

        <p className={`text-[10px] text-muted mt-1 ${isUser ? 'text-right' : 'text-left'} px-1`}>
          {time}
        </p>
      </div>
    </motion.div>
  );
});
