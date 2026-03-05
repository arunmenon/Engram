import type { PipelineStats } from '../../api/pipeline';

interface PipelineStatusProps {
  backendConnected: boolean;
  pipelineStats: PipelineStats;
  ingestedEvents: number;
}

/**
 * PipelineStatus — displays the state of each Context Graph consumer
 * with real node/edge counts from the backend stats endpoint.
 *
 * Shows which pipeline stages have produced output, helping verify
 * that Ingestion -> Projection -> Extraction -> Enrichment -> Consolidation
 * are all working end-to-end.
 */
export function PipelineStatus({ backendConnected, pipelineStats, ingestedEvents }: PipelineStatusProps) {
  if (!backendConnected) return null;

  const nc = pipelineStats.nodeCounts;
  const ec = pipelineStats.edgeCounts;

  // Consumer status indicators
  const consumers = [
    {
      id: 1,
      name: 'Projection',
      description: 'Events -> Graph nodes',
      active: (nc['Event'] ?? 0) > 0,
      outputs: [
        { label: 'Event', count: nc['Event'] ?? 0, color: 'text-blue-400' },
      ],
      edges: [
        { label: 'FOLLOWS', count: ec['FOLLOWS'] ?? 0 },
        { label: 'CAUSED_BY', count: ec['CAUSED_BY'] ?? 0 },
      ],
    },
    {
      id: 2,
      name: 'Extraction',
      description: 'Session end -> Entities + Profile',
      active: (nc['Entity'] ?? 0) > 0 || (nc['UserProfile'] ?? 0) > 0,
      outputs: [
        { label: 'Entity', count: nc['Entity'] ?? 0, color: 'text-teal-400' },
        { label: 'UserProfile', count: nc['UserProfile'] ?? 0, color: 'text-purple-400' },
        { label: 'Preference', count: nc['Preference'] ?? 0, color: 'text-green-400' },
        { label: 'Skill', count: nc['Skill'] ?? 0, color: 'text-purple-300' },
      ],
      edges: [
        { label: 'REFERENCES', count: ec['REFERENCES'] ?? 0 },
        { label: 'HAS_PROFILE', count: ec['HAS_PROFILE'] ?? 0 },
        { label: 'HAS_PREFERENCE', count: ec['HAS_PREFERENCE'] ?? 0 },
        { label: 'DERIVED_FROM', count: ec['DERIVED_FROM'] ?? 0 },
      ],
    },
    {
      id: 3,
      name: 'Enrichment',
      description: 'Keywords + importance + embeddings',
      active: (nc['Event'] ?? 0) > 0,
      outputs: [
        { label: 'enriched', count: nc['Event'] ?? 0, color: 'text-blue-300' },
      ],
      edges: (ec['SIMILAR_TO'] ?? 0) > 0
        ? [{ label: 'SIMILAR_TO', count: ec['SIMILAR_TO'] ?? 0 }]
        : [],
    },
    {
      id: 4,
      name: 'Consolidation',
      description: 'Summaries + forgetting',
      active: (nc['Summary'] ?? 0) > 0,
      outputs: [
        { label: 'Summary', count: nc['Summary'] ?? 0, color: 'text-gray-400' },
        { label: 'Episode', count: nc['Episode'] ?? 0, color: 'text-amber-400' },
      ],
      edges: [
        { label: 'SUMMARIZES', count: ec['SUMMARIZES'] ?? 0 },
      ],
    },
  ];

  return (
    <div className="px-3 py-2 border-b border-muted-dark/20">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[9px] font-semibold text-muted uppercase tracking-wider">
          Pipeline Status
        </span>
        <span className="text-[9px] font-mono text-muted">
          Stream: {pipelineStats.streamLength} events
        </span>
        {ingestedEvents > 0 && (
          <span className="text-[9px] font-mono text-green-400/70">
            ({ingestedEvents} ingested this session)
          </span>
        )}
      </div>

      <div className="grid grid-cols-4 gap-1.5">
        {consumers.map(c => (
          <div
            key={c.id}
            className={`rounded px-2 py-1 text-[8px] ${
              c.active
                ? 'bg-green-500/10 border border-green-500/20'
                : 'bg-surface-hover border border-muted-dark/10'
            }`}
          >
            <div className="flex items-center gap-1 mb-0.5">
              <div className={`w-1.5 h-1.5 rounded-full ${
                c.active ? 'bg-green-400' : 'bg-gray-600'
              }`} />
              <span className={`font-semibold ${
                c.active ? 'text-green-400' : 'text-gray-500'
              }`}>
                C{c.id}: {c.name}
              </span>
            </div>
            <div className="text-[7px] text-muted mb-0.5">{c.description}</div>
            <div className="flex flex-wrap gap-x-1.5 gap-y-0.5">
              {c.outputs
                .filter(o => o.count > 0)
                .map(o => (
                  <span key={o.label} className={`font-mono ${o.color}`}>
                    {o.count} {o.label}
                  </span>
                ))}
              {c.edges
                .filter(e => e.count > 0)
                .map(e => (
                  <span key={e.label} className="font-mono text-muted">
                    {e.count} {e.label}
                  </span>
                ))}
              {c.outputs.every(o => o.count === 0) && c.edges.every(e => e.count === 0) && (
                <span className="text-gray-600 italic">no output yet</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
