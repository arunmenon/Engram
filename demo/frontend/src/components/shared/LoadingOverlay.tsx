import { Loader2 } from 'lucide-react';

export function LoadingOverlay() {
  return (
    <div className="absolute inset-0 bg-surface/80 backdrop-blur-sm flex items-center justify-center z-10">
      <div className="flex items-center gap-2 text-muted-light">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm font-medium">Loading...</span>
      </div>
    </div>
  );
}
