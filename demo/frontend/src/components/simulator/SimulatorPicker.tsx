import { Play, MessageSquare, GitBranch, Users } from 'lucide-react';
import { allScenarios } from '../../data/scenarios';
import { useSimulatorStore } from '../../stores/simulatorStore';

export function SimulatorPicker() {
  const pickScenario = useSimulatorStore(s => s.pickScenario);

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 overflow-y-auto">
      <div className="w-full max-w-sm space-y-4">
        <div className="text-center space-y-2 mb-6">
          <div className="flex items-center justify-center gap-2">
            <GitBranch className="w-5 h-5 text-accent-blue" />
            <h2 className="text-sm font-semibold text-gray-100">Context Graph Simulator</h2>
          </div>
          <p className="text-xs text-muted leading-relaxed">
            Watch how context accumulates across conversation turns.
            The graph grows as entities, preferences, and patterns emerge.
          </p>
        </div>

        {allScenarios.map(scenario => (
          <button
            key={scenario.id}
            onClick={() => pickScenario(scenario.id)}
            className="w-full group text-left bg-surface-hover/50 hover:bg-surface-hover border border-muted-dark/30 hover:border-accent-blue/40 rounded-xl p-4 transition-all"
          >
            {/* Persona header */}
            <div className="flex items-center gap-3 mb-3">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white"
                style={{ backgroundColor: scenario.persona.color }}
              >
                {scenario.persona.avatar}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-100">{scenario.title}</div>
                <div className="text-xs text-muted">{scenario.subtitle}</div>
              </div>
              <Play className="w-4 h-4 text-muted group-hover:text-accent-blue transition-colors" />
            </div>

            {/* Description */}
            <p className="text-[11px] text-muted-light leading-relaxed mb-3">
              {scenario.description}
            </p>

            {/* Stats */}
            <div className="flex items-center gap-4 text-[10px] text-muted">
              <span className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                {scenario.sessions.length} sessions
              </span>
              <span className="flex items-center gap-1">
                <MessageSquare className="w-3 h-3" />
                {scenario.messages.length} messages
              </span>
              <span className="flex items-center gap-1">
                <GitBranch className="w-3 h-3" />
                {scenario.atlasSnapshots[scenario.atlasSnapshots.length - 1]?.nodes.length ?? 0} nodes
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
