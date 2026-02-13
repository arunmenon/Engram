import { ConfidenceBar } from './ConfidenceBar';
import type { GraphNode } from '../../types/graph';
import { useGraphStore } from '../../stores/graphStore';
import { useInsightStore } from '../../stores/insightStore';
import { NODE_TYPE_BADGE_COLORS } from '../../data/constants';

interface NodeCardProps {
  node: GraphNode;
  compact?: boolean;
}

export function NodeCard({ node, compact = false }: NodeCardProps) {
  const selectNode = useGraphStore(s => s.selectNode);
  const setSelectedNode = useInsightStore(s => s.setSelectedNode);

  const handleClick = () => {
    selectNode(node.id);
    setSelectedNode(node.id);
  };

  return (
    <button
      onClick={handleClick}
      className="w-full text-left p-3 rounded-lg bg-surface-card hover:bg-surface-hover border border-transparent hover:border-muted-dark/50 transition-all"
    >
      <div className="flex items-center justify-between mb-1">
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${NODE_TYPE_BADGE_COLORS[node.node_type] || 'bg-muted-dark/40 text-muted-light'}`}>
          {node.node_type}
        </span>
        {!compact && (
          <span className="text-[10px] text-muted font-mono">
            {node.decay_score.toFixed(2)}
          </span>
        )}
      </div>
      <p className="text-sm text-gray-200 font-medium truncate">{node.label}</p>
      {!compact && (
        <>
          {node.event_type && (
            <p className="text-xs text-muted mt-0.5 font-mono">{node.event_type}</p>
          )}
          <ConfidenceBar value={node.decay_score} className="mt-2" />
        </>
      )}
    </button>
  );
}
