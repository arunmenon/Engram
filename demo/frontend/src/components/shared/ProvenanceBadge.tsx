import { FileText } from 'lucide-react';
import { useSessionStore } from '../../stores/sessionStore';

interface ProvenanceBadgeProps {
  nodeIds: string[];
  count: number;
}

export function ProvenanceBadge({ nodeIds, count }: ProvenanceBadgeProps) {
  const setHighlightedNodes = useSessionStore(s => s.setHighlightedNodes);

  return (
    <button
      onClick={() => setHighlightedNodes(nodeIds)}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-surface-hover text-muted-light hover:bg-accent-blue/20 hover:text-accent-blue transition-colors"
    >
      <FileText className="w-3 h-3" />
      {count} source{count !== 1 ? 's' : ''}
    </button>
  );
}
