import { useState } from 'react';
import { Send } from 'lucide-react';
import { isLiveMode } from '../../api/mode';
import { useChatStore } from '../../stores/chatStore';

export function ChatInput() {
  const [value, setValue] = useState('');
  const sendUserMessage = useChatStore(s => s.sendUserMessage);
  const isStreaming = useChatStore(s => s.isStreaming);
  const sessionId = useChatStore(s => s.sessionId);
  const live = isLiveMode();

  const canSend = live && sessionId && value.trim() && !isStreaming;

  const handleSubmit = () => {
    if (!canSend) return;
    sendUserMessage(value.trim());
    setValue('');
  };

  if (!live) {
    return (
      <div className="p-3 border-t border-muted-dark/30">
        <div className="flex items-center gap-2">
          <input
            type="text"
            disabled
            placeholder="Switch to Live mode to enable chat"
            className="flex-1 bg-surface-darker border border-muted-dark/30 rounded-lg px-3 py-2 text-sm text-muted placeholder:text-muted/60 cursor-not-allowed"
          />
          <button
            disabled
            className="p-2 rounded-lg bg-surface-hover text-muted cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-3 border-t border-muted-dark/30">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); }}
          placeholder={sessionId ? 'Type a message...' : 'Pick a scenario to start'}
          disabled={!sessionId || isStreaming}
          className="flex-1 bg-surface-darker border border-muted-dark/30 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder:text-muted/60 focus:outline-none focus:ring-1 focus:ring-accent-blue/50 disabled:cursor-not-allowed disabled:text-muted"
        />
        <button
          onClick={handleSubmit}
          disabled={!canSend}
          className={`p-2 rounded-lg transition-colors ${
            canSend
              ? 'bg-accent-blue text-white hover:bg-accent-blue/80'
              : 'bg-surface-hover text-muted cursor-not-allowed'
          }`}
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
