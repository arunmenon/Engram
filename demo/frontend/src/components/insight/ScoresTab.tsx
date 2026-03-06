import { useState, useMemo } from 'react';
import { Target } from 'lucide-react';
import { useGraphStore } from '../../stores/graphStore';
import { ScoreRadar } from '../shared/ScoreRadar';
import { DecayCurve } from '../shared/DecayCurve';

export function ScoresTab() {
  const selectedNodeId = useGraphStore(s => s.selectedNodeId);
  const nodes = useGraphStore(s => s.nodes);
  const node = nodes.find(n => n.id === selectedNodeId);

  const [weights, setWeights] = useState({
    recency: 1.0,
    importance: 1.0,
    relevance: 1.0,
    user_affinity: 0.5,
  });

  const factors = useMemo(() => {
    if (!node) return null;
    return {
      recency: node.decay_score,
      importance: node.importance / 10,
      relevance: 0.8,
      user_affinity: 0.5,
    };
  }, [node]);

  const composite = useMemo(() => {
    if (!factors) return 0;
    const sum = weights.recency + weights.importance + weights.relevance + weights.user_affinity;
    if (sum === 0) return 0;
    return (
      (factors.recency * weights.recency +
        factors.importance * weights.importance +
        factors.relevance * weights.relevance +
        factors.user_affinity * weights.user_affinity) /
      sum
    );
  }, [factors, weights]);

  if (!node || !factors) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Target className="w-8 h-8 text-muted mb-3" />
        <p className="text-sm text-muted-light">Select a node in the graph to see scoring details</p>
      </div>
    );
  }

  const typeColors: Record<string, string> = {
    Event: 'bg-accent-blue/20 text-accent-blue',
    Entity: 'bg-accent-teal/20 text-accent-teal',
    Preference: 'bg-accent-green/20 text-accent-green',
    Skill: 'bg-accent-purple/20 text-accent-purple',
    Summary: 'bg-muted-dark/40 text-muted-light',
    UserProfile: 'bg-purple-500/20 text-purple-400',
    BehavioralPattern: 'bg-accent-amber/20 text-accent-amber',
    Workflow: 'bg-accent-amber/20 text-accent-amber',
  };

  const factorRows = [
    { name: 'Recency', key: 'recency' as const, raw: factors.recency },
    { name: 'Importance', key: 'importance' as const, raw: factors.importance },
    { name: 'Relevance', key: 'relevance' as const, raw: factors.relevance },
    { name: 'User Affinity', key: 'user_affinity' as const, raw: factors.user_affinity },
  ];

  return (
    <div className="space-y-4">
      {/* Node Header */}
      <div className="flex items-center gap-2">
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${typeColors[node.node_type] || 'bg-muted-dark/40 text-muted-light'}`}>
          {node.node_type}
        </span>
        <span className="text-sm font-medium text-gray-200 truncate">{node.label}</span>
      </div>

      {/* Score Radar */}
      <ScoreRadar scores={factors} />

      {/* Decay Curve */}
      <div>
        <h4 className="text-xs font-semibold text-muted-light uppercase tracking-wider mb-2">Decay Curve</h4>
        <DecayCurve initialScore={node.decay_score} importance={node.importance} />
      </div>

      {/* Scoring Weights */}
      <div>
        <h4 className="text-xs font-semibold text-muted-light uppercase tracking-wider mb-2">Scoring Weights</h4>
        <div className="space-y-2">
          {factorRows.map(({ name, key }) => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs text-muted-light w-24">{name}</span>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={weights[key]}
                onChange={e => setWeights(prev => ({ ...prev, [key]: parseFloat(e.target.value) }))}
                className="flex-1 h-1 accent-accent-blue"
              />
              <span className="text-xs text-muted font-mono w-8 text-right">
                {weights[key].toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Composite Score */}
      <div className="p-3 rounded-lg bg-surface-card border border-muted-dark/30 text-center">
        <p className="text-xs text-muted-light mb-1">Composite Score</p>
        <p className="text-2xl font-bold text-accent-blue font-mono">{composite.toFixed(3)}</p>
      </div>

      {/* Factor Breakdown */}
      <div>
        <h4 className="text-xs font-semibold text-muted-light uppercase tracking-wider mb-2">Factor Breakdown</h4>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted border-b border-muted-dark/30">
              <th className="text-left py-1 font-medium">Factor</th>
              <th className="text-right py-1 font-medium">Raw</th>
              <th className="text-right py-1 font-medium">Weight</th>
              <th className="text-right py-1 font-medium">Weighted</th>
            </tr>
          </thead>
          <tbody>
            {factorRows.map(({ name, key, raw }) => (
              <tr key={key} className="text-muted-light border-b border-muted-dark/20">
                <td className="py-1">{name}</td>
                <td className="text-right font-mono">{raw.toFixed(2)}</td>
                <td className="text-right font-mono">{weights[key].toFixed(1)}</td>
                <td className="text-right font-mono text-gray-200">{(raw * weights[key]).toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
