import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

interface ScoreRadarProps {
  scores: {
    recency: number;
    importance: number;
    relevance: number;
    user_affinity: number;
  };
}

export function ScoreRadar({ scores }: ScoreRadarProps) {
  const data = [
    { factor: 'Recency', value: scores.recency },
    { factor: 'Importance', value: scores.importance },
    { factor: 'Relevance', value: scores.relevance },
    { factor: 'User Affinity', value: scores.user_affinity },
  ];

  return (
    <div className="w-full h-52">
      <ResponsiveContainer>
        <RadarChart data={data}>
          <PolarGrid stroke="#2a2a35" />
          <PolarAngleAxis
            dataKey="factor"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
          />
          <PolarRadiusAxis
            domain={[0, 1]}
            tick={{ fill: '#71717a', fontSize: 10 }}
            stroke="#2a2a35"
          />
          <Radar
            dataKey="value"
            stroke="#3b82f6"
            fill="#3b82f6"
            fillOpacity={0.2}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
