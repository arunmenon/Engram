interface IntentChartProps {
  intents: { intent: string; score: number }[];
}

export function IntentChart({ intents }: IntentChartProps) {
  const sorted = [...intents].sort((a, b) => b.score - a.score);

  return (
    <div className="space-y-2">
      {sorted.map(({ intent, score }) => (
        <div key={intent} className="flex items-center gap-2">
          <span className="text-xs text-muted-light w-20 text-right font-mono">{intent}</span>
          <div className="flex-1 h-4 bg-surface-darker rounded overflow-hidden">
            <div
              className="h-full rounded bg-accent-blue/60 transition-all duration-500"
              style={{ width: `${score * 100}%` }}
            />
          </div>
          <span className="text-xs text-muted font-mono w-8">{score.toFixed(1)}</span>
        </div>
      ))}
    </div>
  );
}
