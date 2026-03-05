import { useDebugStore } from '../../stores/debugStore';

const statusStyles: Record<string, { dot: string; text: string }> = {
  healthy: { dot: 'bg-green-400', text: 'text-green-400' },
  lagging: { dot: 'bg-amber-400', text: 'text-amber-400' },
  idle: { dot: 'bg-gray-500', text: 'text-gray-500' },
};

export function ConsumerStatus() {
  const consumerGroups = useDebugStore((s) => s.consumerGroups);

  return (
    <div className="grid grid-cols-2 gap-1.5">
      {consumerGroups.map((group) => {
        const style = statusStyles[group.status];
        return (
          <div key={group.stream_group} className="p-2 rounded bg-surface-darker/50 border border-muted-dark/20">
            <div className="flex items-center gap-1.5 mb-1">
              <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
              <span className="text-[10px] font-medium text-gray-200 truncate">{group.name}</span>
            </div>
            <div className="text-[9px] text-muted space-y-0.5">
              <div className="flex justify-between">
                <span>Pending</span>
                <span className={`font-mono ${group.pending > 10 ? 'text-amber-400' : 'text-muted-light'}`}>
                  {group.pending}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Lag</span>
                <span className="font-mono text-muted-light">{group.lag}</span>
              </div>
              <div className="flex justify-between">
                <span>Consumers</span>
                <span className="font-mono text-muted-light">{group.consumers}</span>
              </div>
              <div className="flex justify-between">
                <span>Status</span>
                <span className={`font-medium uppercase ${style.text}`}>{group.status}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
