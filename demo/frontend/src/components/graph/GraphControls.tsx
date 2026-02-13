import { useGraphStore } from '../../stores/graphStore';
import type { NodeType } from '../../types/atlas';
import { LayoutGrid, Circle } from 'lucide-react';

const NODE_TYPE_CONFIG: { type: NodeType; label: string; color: string }[] = [
  { type: 'Event', label: 'Event', color: '#3b82f6' },
  { type: 'Entity', label: 'Entity', color: '#14b8a6' },
  { type: 'Preference', label: 'Pref', color: '#22c55e' },
  { type: 'Skill', label: 'Skill', color: '#a855f7' },
  { type: 'Summary', label: 'Summary', color: '#4b5563' },
  { type: 'UserProfile', label: 'Profile', color: '#8b5cf6' },
  { type: 'BehavioralPattern', label: 'Pattern', color: '#f59e0b' },
  { type: 'Workflow', label: 'Workflow', color: '#f59e0b' },
];

const SESSION_OPTIONS = [
  { id: null, label: 'All' },
  { id: 'session-1', label: 'S1' },
  { id: 'session-2', label: 'S2' },
  { id: 'session-3', label: 'S3' },
];

export function GraphControls() {
  const layoutType = useGraphStore((s) => s.layoutType);
  const setLayoutType = useGraphStore((s) => s.setLayoutType);
  const visibleNodeTypes = useGraphStore((s) => s.visibleNodeTypes);
  const toggleNodeType = useGraphStore((s) => s.toggleNodeType);
  const sessionFilter = useGraphStore((s) => s.sessionFilter);
  const setSessionFilter = useGraphStore((s) => s.setSessionFilter);

  return (
    <div className="absolute top-3 right-3 z-40 bg-surface-dark/80 backdrop-blur-sm border border-muted-dark/40 rounded-lg p-2.5 space-y-2.5 min-w-[180px]">
      {/* Layout toggle */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => setLayoutType('force')}
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
            layoutType === 'force'
              ? 'bg-accent-blue/20 text-accent-blue'
              : 'text-muted-light hover:text-gray-100'
          }`}
        >
          <LayoutGrid size={12} />
          Force
        </button>
        <button
          onClick={() => setLayoutType('circular')}
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
            layoutType === 'circular'
              ? 'bg-accent-blue/20 text-accent-blue'
              : 'text-muted-light hover:text-gray-100'
          }`}
        >
          <Circle size={12} />
          Circular
        </button>
      </div>

      {/* Separator */}
      <div className="h-px bg-muted-dark/40" />

      {/* Node type filters */}
      <div className="flex flex-wrap gap-1">
        {NODE_TYPE_CONFIG.map(({ type, label, color }) => {
          const isActive = visibleNodeTypes.has(type);
          return (
            <button
              key={type}
              onClick={() => toggleNodeType(type)}
              className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium transition-all ${
                isActive ? 'text-gray-200' : 'text-muted-dark'
              }`}
            >
              <span
                className="inline-block w-2 h-2 rounded-full shrink-0 transition-opacity"
                style={{
                  backgroundColor: color,
                  opacity: isActive ? 1 : 0.25,
                }}
              />
              {label}
            </button>
          );
        })}
      </div>

      {/* Separator */}
      <div className="h-px bg-muted-dark/40" />

      {/* Session filter */}
      <div className="flex items-center gap-1">
        {SESSION_OPTIONS.map(({ id, label }) => (
          <button
            key={label}
            onClick={() => setSessionFilter(id)}
            className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
              sessionFilter === id
                ? 'bg-accent-blue/20 text-accent-blue'
                : 'text-muted-light hover:text-gray-100'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
