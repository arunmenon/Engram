import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Info, ChevronDown } from 'lucide-react';
import type { NodeType } from '../../types/atlas';

type ShapeType = 'circle' | 'diamond' | 'triangle' | 'square';

const NODE_LEGEND: { type: NodeType; label: string; color: string; shape: ShapeType }[] = [
  { type: 'Event', label: 'Event', color: '#3b82f6', shape: 'circle' },
  { type: 'Entity', label: 'Entity', color: '#14b8a6', shape: 'triangle' },
  { type: 'Summary', label: 'Summary', color: '#4b5563', shape: 'square' },
  { type: 'UserProfile', label: 'User Profile', color: '#8b5cf6', shape: 'circle' },
  { type: 'Preference', label: 'Preference', color: '#22c55e', shape: 'diamond' },
  { type: 'Skill', label: 'Skill', color: '#a855f7', shape: 'diamond' },
  { type: 'Workflow', label: 'Workflow', color: '#f59e0b', shape: 'triangle' },
  { type: 'BehavioralPattern', label: 'Pattern', color: '#f59e0b', shape: 'square' },
];

function ShapeIcon({ shape, color }: { shape: ShapeType; color: string }) {
  const size = 10;
  switch (shape) {
    case 'circle':
      return (
        <svg width={size} height={size} viewBox="0 0 10 10" className="shrink-0">
          <circle cx="5" cy="5" r="4.5" fill={color} />
        </svg>
      );
    case 'diamond':
      return (
        <svg width={size} height={size} viewBox="0 0 10 10" className="shrink-0">
          <polygon points="5,0.5 9.5,5 5,9.5 0.5,5" fill={color} />
        </svg>
      );
    case 'triangle':
      return (
        <svg width={size} height={size} viewBox="0 0 10 10" className="shrink-0">
          <polygon points="5,0.5 9.5,9.5 0.5,9.5" fill={color} />
        </svg>
      );
    case 'square':
      return (
        <svg width={size} height={size} viewBox="0 0 10 10" className="shrink-0">
          <rect x="0.5" y="0.5" width="9" height="9" fill={color} />
        </svg>
      );
  }
}

type EdgeLineStyle = 'solid' | 'dashed' | 'dotted';

function EdgeLine({ color, style, hasArrow, label }: { color: string; style: EdgeLineStyle; hasArrow?: boolean; label?: string }) {
  return (
    <svg width="32" height="12" className="shrink-0">
      <line
        x1="0"
        y1="6"
        x2={hasArrow ? 24 : 32}
        y2="6"
        stroke={color}
        strokeWidth={style === 'solid' ? 2 : 1.5}
        strokeDasharray={style === 'dashed' ? '4,3' : style === 'dotted' ? '2,2' : 'none'}
      />
      {hasArrow && <polygon points="24,2 32,6 24,10" fill={color} />}
      {label && (
        <text x="16" y="4" textAnchor="middle" fill={color} fontSize="6" fontFamily="monospace">
          {label}
        </text>
      )}
    </svg>
  );
}

interface EdgeLegendItem {
  label: string;
  color: string;
  style: EdgeLineStyle;
  hasArrow?: boolean;
  edgeLabel?: string;
}

const EDGE_GROUPS: { title: string; items: EdgeLegendItem[] }[] = [
  {
    title: 'Arrows',
    items: [
      { label: 'Follows', color: '#374151', style: 'solid', hasArrow: true },
      { label: 'Caused By', color: '#ef4444', style: 'solid', hasArrow: true },
      { label: 'References', color: '#22c55e', style: 'solid', hasArrow: true },
      { label: 'Derived From', color: '#fb923c', style: 'solid', hasArrow: true, edgeLabel: 'LLM' },
    ],
  },
  {
    title: 'Dashed',
    items: [
      { label: 'Similar To', color: '#60a5fa', style: 'dashed' },
    ],
  },
  {
    title: 'Dotted',
    items: [
      { label: 'Has Preference', color: '#a78bfa', style: 'dotted' },
      { label: 'Has Skill', color: '#a78bfa', style: 'dotted' },
      { label: 'Has Profile', color: '#a78bfa', style: 'dotted' },
      { label: 'Interested In', color: '#a78bfa', style: 'dotted' },
      { label: 'About', color: '#a78bfa', style: 'dotted' },
    ],
  },
  {
    title: 'Solid',
    items: [
      { label: 'Summarizes', color: '#4b5563', style: 'solid' },
      { label: 'Same As', color: '#14b8a6', style: 'solid' },
      { label: 'Related To', color: '#14b8a6', style: 'solid' },
      { label: 'Exhibits Pattern', color: '#f59e0b', style: 'solid' },
    ],
  },
];

export function GraphLegend() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="absolute bottom-3 right-3 z-40">
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="bg-surface-dark/90 backdrop-blur-sm border border-muted-dark/40 rounded-lg p-3 mb-1.5 min-w-[200px]"
          >
            {/* Nodes section */}
            <p className="text-[10px] font-mono uppercase tracking-wider text-muted mb-1.5">
              Nodes
            </p>
            <div className="space-y-1 mb-3">
              {NODE_LEGEND.map(({ type, label, color, shape }) => (
                <div key={type} className="flex items-center gap-2">
                  <ShapeIcon shape={shape} color={color} />
                  <span className="text-xs text-gray-300">{label}</span>
                </div>
              ))}
            </div>

            {/* Edges section */}
            <p className="text-[10px] font-mono uppercase tracking-wider text-muted mb-1.5">
              Edges
            </p>
            <div className="space-y-2">
              {EDGE_GROUPS.map(group => (
                <div key={group.title} className="space-y-1">
                  {group.items.map(item => (
                    <div key={item.label} className="flex items-center gap-2">
                      <EdgeLine
                        color={item.color}
                        style={item.style}
                        hasArrow={item.hasArrow}
                        label={item.edgeLabel}
                      />
                      <span className="text-xs text-gray-300">{item.label}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 bg-surface-dark/80 backdrop-blur-sm border border-muted-dark/40 rounded-lg px-2.5 py-1.5 text-xs text-muted-light hover:text-gray-100 transition-colors"
      >
        <Info size={13} />
        Legend
        <ChevronDown
          size={12}
          className={`transition-transform ${expanded ? 'rotate-180' : ''}`}
        />
      </button>
    </div>
  );
}
