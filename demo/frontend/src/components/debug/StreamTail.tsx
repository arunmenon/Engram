import { useRef, useEffect } from 'react';
import { useDebugStore } from '../../stores/debugStore';

const eventTypeColors: Record<string, string> = {
  'agent.invoke': 'bg-blue-500/20 text-blue-400',
  'agent.respond': 'bg-purple-500/20 text-purple-400',
  'tool.execute': 'bg-amber-500/20 text-amber-400',
  'tool.result': 'bg-green-500/20 text-green-400',
  'system.session_start': 'bg-teal-500/20 text-teal-400',
  'system.session_end': 'bg-gray-500/20 text-gray-400',
};

export function StreamTail() {
  const streamEvents = useDebugStore((s) => s.streamEvents);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [streamEvents]);

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto font-mono text-[10px]">
      <table className="w-full">
        <thead>
          <tr className="text-muted uppercase tracking-wider sticky top-0 bg-surface-card">
            <th className="text-left py-1 px-1.5 font-medium">Position</th>
            <th className="text-left py-1 px-1.5 font-medium">Type</th>
            <th className="text-left py-1 px-1.5 font-medium">Session</th>
            <th className="text-right py-1 px-1.5 font-medium">Size</th>
          </tr>
        </thead>
        <tbody>
          {streamEvents.map((evt) => {
            const colorClass = eventTypeColors[evt.event_type] ?? 'bg-gray-500/20 text-gray-400';
            return (
              <tr key={evt.global_position} className="border-t border-muted-dark/10 hover:bg-surface-hover/20">
                <td className="py-0.5 px-1.5 text-muted-light tabular-nums">{evt.global_position.slice(-8)}</td>
                <td className="py-0.5 px-1.5">
                  <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-medium ${colorClass}`}>
                    {evt.event_type}
                  </span>
                </td>
                <td className="py-0.5 px-1.5 text-muted-light">{evt.session_id}</td>
                <td className="py-0.5 px-1.5 text-right text-muted tabular-nums">{evt.size_bytes}B</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
