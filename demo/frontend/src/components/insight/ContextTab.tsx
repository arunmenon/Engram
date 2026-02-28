import { useSessionStore } from '../../stores/sessionStore';
import { useGraphStore } from '../../stores/graphStore';
import { IntentChart } from '../shared/IntentChart';
import { NodeCard } from '../shared/NodeCard';
import { sessionIntents } from '../../data/mockScores';

export function ContextTab() {
  const currentSessionId = useSessionStore(s => s.currentSessionId);
  const nodes = useGraphStore(s => s.nodes);
  const intents = sessionIntents[currentSessionId] || [];

  const sessionNodes = nodes.filter(n =>
    n.session_id === currentSessionId ||
    ['Entity', 'Preference', 'UserProfile'].includes(n.node_type)
  );

  const globalNodes = nodes.filter(n =>
    !['Entity', 'Preference', 'UserProfile'].includes(n.node_type) &&
    n.session_id !== currentSessionId
  );

  const queryMs = currentSessionId === 'session-3' ? 145 : currentSessionId === 'session-2' ? 87 : 52;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium text-gray-100">Retrieved Context</h3>
        <p className="text-xs text-muted mt-0.5">
          <span className="inline-flex items-center gap-1">
            <span className="px-1.5 py-0.5 rounded bg-accent-blue/15 text-accent-blue font-medium">{sessionNodes.length}</span>
            session
          </span>
          {' / '}
          <span className="inline-flex items-center gap-1">
            <span className="px-1.5 py-0.5 rounded bg-muted-dark/40 text-muted-light font-medium">{globalNodes.length}</span>
            global
          </span>
          {' '}&middot; {queryMs}ms
        </p>
      </div>

      <IntentChart intents={intents} />

      <div className="border-t border-muted-dark/30 pt-3">
        <div className="space-y-2">
          {sessionNodes.map(node => (
            <NodeCard key={node.id} node={node} />
          ))}
        </div>
      </div>
    </div>
  );
}
