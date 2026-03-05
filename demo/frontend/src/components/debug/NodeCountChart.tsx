import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { useDebugStore } from '../../stores/debugStore';

const nodeTypeColors: Record<string, string> = {
  Event: '#3b82f6',
  Entity: '#14b8a6',
  Summary: '#4b5563',
  UserProfile: '#8b5cf6',
  Preference: '#22c55e',
  Skill: '#a855f7',
  Workflow: '#f59e0b',
  BehavioralPattern: '#f59e0b',
};

export function NodeCountChart() {
  const nodeCountsByType = useDebugStore((s) => s.nodeCountsByType);

  const data = Object.entries(nodeCountsByType).map(([name, count]) => ({
    name,
    count,
    color: nodeTypeColors[name] ?? '#6b7280',
  }));

  return (
    <div className="h-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: -10 }}>
          <XAxis
            dataKey="name"
            tick={{ fontSize: 8, fill: '#6b7280' }}
            axisLine={false}
            tickLine={false}
            interval={0}
            angle={-45}
            textAnchor="end"
            height={50}
          />
          <YAxis
            tick={{ fontSize: 8, fill: '#6b7280' }}
            axisLine={false}
            tickLine={false}
            width={30}
          />
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
