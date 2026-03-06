import type { PatternObservation } from '../../types/behavioral';

interface PatternTimelineProps {
  observations: PatternObservation[];
}

export function PatternTimeline({ observations }: PatternTimelineProps) {
  return (
    <div className="relative pl-4 space-y-3">
      {/* Vertical line */}
      <div className="absolute left-[7px] top-1 bottom-1 w-px bg-muted-dark/50" />

      {observations.map((obs, i) => {
        const isPositive = obs.confidence_delta >= 0;
        const deltaColor = isPositive ? 'text-green-400' : 'text-red-400';
        const dotColor = isPositive ? 'bg-green-400' : 'bg-red-400';

        return (
          <div key={i} className="relative">
            {/* Dot on timeline */}
            <div className={`absolute -left-4 top-1.5 w-2 h-2 rounded-full ${dotColor} ring-2 ring-surface-card`} />

            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-muted">
                  {new Date(obs.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
                <span className="text-[9px] px-1 py-0.5 rounded bg-accent-blue/15 text-accent-blue font-mono">
                  {obs.session_id}
                </span>
                <span className={`text-[10px] font-mono ${deltaColor}`}>
                  {isPositive ? '+' : ''}{(obs.confidence_delta * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-[11px] text-gray-300 leading-snug">{obs.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
