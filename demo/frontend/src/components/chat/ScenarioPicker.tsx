import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { isLiveMode } from '../../api/mode';

export function ScenarioPicker() {
  const scenarios = useChatStore(s => s.scenarios);
  const startScenario = useChatStore(s => s.startScenario);
  const isStreaming = useChatStore(s => s.isStreaming);
  const error = useChatStore(s => s.error);
  const fetchScenarios = useChatStore(s => s.fetchScenarios);

  useEffect(() => {
    if (isLiveMode() && scenarios.length === 0) {
      fetchScenarios();
    }
  }, [fetchScenarios, scenarios.length]);

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4">
      <h2 className="text-lg font-semibold text-gray-100 mb-1">Choose a Scenario</h2>
      <p className="text-xs text-muted-light mb-4">Pick a support scenario to begin</p>
      {error && (
        <p className="text-xs text-red-400 mb-3">{error}</p>
      )}
      {scenarios.length === 0 && !error && (
        <div className="flex items-center gap-2 text-muted-light text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading scenarios...
        </div>
      )}
      <div className="space-y-2 w-full max-w-sm">
        {scenarios.map(s => (
          <button
            key={s.id}
            onClick={() => startScenario(s.id)}
            disabled={isStreaming}
            className="w-full text-left p-3 rounded-lg bg-surface-card border border-muted-dark/30 hover:border-muted-dark/60 hover:bg-surface-hover transition-all disabled:opacity-50"
          >
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
              <span className="text-sm font-medium text-gray-100">{s.title}</span>
            </div>
            <p className="text-xs text-muted-light">{s.description}</p>
            <p className="text-[10px] text-muted mt-1">Persona: {s.persona_name}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
