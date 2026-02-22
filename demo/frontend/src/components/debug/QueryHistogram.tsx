import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { useDebugStore } from '../../stores/debugStore';

export function QueryHistogram() {
  const histogram = useDebugStore((s) => s.queryLatencyHistogram);

  return (
    <div className="h-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={histogram} margin={{ top: 4, right: 4, bottom: 4, left: -10 }}>
          <XAxis
            dataKey="range"
            tick={{ fontSize: 8, fill: '#6b7280' }}
            axisLine={false}
            tickLine={false}
            interval={0}
            angle={-45}
            textAnchor="end"
            height={40}
          />
          <YAxis
            tick={{ fontSize: 8, fill: '#6b7280' }}
            axisLine={false}
            tickLine={false}
            width={30}
          />
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {histogram.map((entry) => (
              <Cell key={entry.range} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
