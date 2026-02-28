import { AlertTriangle, X } from 'lucide-react';
import { useState } from 'react';

interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  return (
    <div className="absolute top-2 left-2 right-2 z-20 flex items-center gap-2 p-2 rounded-lg bg-red-500/15 border border-red-500/30 text-red-400 text-xs">
      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
      <span className="flex-1 truncate">{message}</span>
      <button onClick={handleDismiss} className="shrink-0 p-0.5 hover:bg-red-500/20 rounded">
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}
