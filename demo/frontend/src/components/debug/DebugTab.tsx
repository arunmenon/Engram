import { StreamTail } from './StreamTail';
import { ConsumerStatus } from './ConsumerStatus';
import { NodeCountChart } from './NodeCountChart';
import { QueryHistogram } from './QueryHistogram';
import { useDebugStore } from '../../stores/debugStore';

export function DebugTab() {
  const nodeCountsByType = useDebugStore((s) => s.nodeCountsByType);
  const totalNodes = Object.values(nodeCountsByType).reduce((sum, c) => sum + c, 0);
  const streamEvents = useDebugStore((s) => s.streamEvents);

  return (
    <div className="space-y-3">
      {/* Stats Summary */}
      <div className="flex items-center gap-3">
        <div className="text-[10px] text-muted">
          Total nodes: <span className="text-gray-200 font-mono font-medium">{totalNodes}</span>
        </div>
        <div className="text-[10px] text-muted">
          Stream events: <span className="text-gray-200 font-mono font-medium">{streamEvents.length}</span>
        </div>
      </div>

      {/* Stream Tail */}
      <div>
        <h4 className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-1">Event Stream</h4>
        <div className="h-48 rounded bg-surface-card border border-muted-dark/30 overflow-hidden">
          <StreamTail />
        </div>
      </div>

      {/* Consumer Groups */}
      <div>
        <h4 className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-1">Consumer Groups</h4>
        <ConsumerStatus />
      </div>

      {/* Node Counts */}
      <div>
        <h4 className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-1">Node Counts by Type</h4>
        <div className="h-40 rounded bg-surface-card border border-muted-dark/30 p-1">
          <NodeCountChart />
        </div>
      </div>

      {/* Query Latency */}
      <div>
        <h4 className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-1">Query Latency (ms)</h4>
        <div className="h-36 rounded bg-surface-card border border-muted-dark/30 p-1">
          <QueryHistogram />
        </div>
      </div>
    </div>
  );
}
