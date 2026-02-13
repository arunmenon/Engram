import { Send } from 'lucide-react';

export function ChatInput() {
  return (
    <div className="p-3 border-t border-muted-dark/30">
      <div className="flex items-center gap-2">
        <input
          type="text"
          disabled
          placeholder="Connect backend to enable chat"
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
