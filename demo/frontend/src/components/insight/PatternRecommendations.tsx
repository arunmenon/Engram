import type { PatternRecommendation } from '../../types/behavioral';

interface PatternRecommendationsProps {
  recommendations: PatternRecommendation[];
}

const priorityStyles: Record<string, string> = {
  high: 'bg-red-500/15 text-red-400',
  medium: 'bg-amber-500/15 text-amber-400',
  low: 'bg-blue-500/15 text-blue-400',
};

export function PatternRecommendations({ recommendations }: PatternRecommendationsProps) {
  return (
    <div className="space-y-2">
      {recommendations.map((rec, i) => (
        <div key={i} className="p-2 rounded bg-surface-darker/50 border border-muted-dark/20">
          <div className="flex items-start gap-2">
            <span className={`shrink-0 text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded ${priorityStyles[rec.priority]}`}>
              {rec.priority}
            </span>
            <div className="min-w-0">
              <p className="text-[11px] text-gray-200 font-medium leading-snug">{rec.action}</p>
              <p className="text-[10px] text-muted mt-0.5 leading-snug">{rec.rationale}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
