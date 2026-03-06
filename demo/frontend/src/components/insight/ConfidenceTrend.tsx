import { LineChart, Line, ResponsiveContainer, Area, AreaChart } from 'recharts';
import type { PatternStatus } from '../../types/behavioral';

interface ConfidenceTrendProps {
  data: Array<{ date: string; confidence: number }>;
  status: PatternStatus;
}

const statusColors: Record<PatternStatus, string> = {
  active: '#22c55e',
  emerging: '#f59e0b',
  declining: '#ef4444',
};

export function ConfidenceTrend({ data, status }: ConfidenceTrendProps) {
  const color = statusColors[status];

  return (
    <div className="w-[120px] h-[40px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <defs>
            <linearGradient id={`gradient-${status}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="confidence"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#gradient-${status})`}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
