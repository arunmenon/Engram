import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { NodeCard } from '../shared/NodeCard';
import { useGraphStore } from '../../stores/graphStore';
import type { GraphNode } from '../../types/graph';

interface ContextUsedProps {
  nodeIds: string[];
  count: number;
}

export function ContextUsed({ nodeIds, count }: ContextUsedProps) {
  const [expanded, setExpanded] = useState(false);
  const nodes = useGraphStore(s => s.nodes);

  const contextNodes = nodeIds
    .map(id => nodes.find(n => n.id === id))
    .filter((n): n is GraphNode => n !== undefined);

  return (
    <div className="mt-1 px-1">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-[11px] text-accent-blue/80 hover:text-accent-blue transition-colors"
      >
        <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? 'rotate-0' : '-rotate-90'}`} />
        {count} context node{count !== 1 ? 's' : ''} used
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-1.5">
              {contextNodes.map(node => (
                <NodeCard key={node.id} node={node} compact />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
