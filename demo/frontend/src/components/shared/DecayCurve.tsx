import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { generateDecayCurve } from '../../data/mockScores';

interface DecayCurveProps {
  initialScore: number;
  importance: number;
}

export function DecayCurve({ initialScore, importance }: DecayCurveProps) {
  const data = generateDecayCurve(initialScore, importance);

  return (
    <div className="w-full h-48">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a35" />
          <XAxis
            dataKey="day"
            tick={{ fill: '#71717a', fontSize: 11 }}
            tickFormatter={(v) => `D${v}`}
            stroke="#2a2a35"
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: '#71717a', fontSize: 11 }}
            stroke="#2a2a35"
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1e1e24', border: '1px solid #2a2a35', borderRadius: 8, color: '#e4e4e7' }}
            formatter={(value: number) => [value.toFixed(3), 'Decay Score']}
            labelFormatter={(label) => `Day ${label}`}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6', r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
