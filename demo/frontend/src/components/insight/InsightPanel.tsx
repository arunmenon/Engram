import { Layers, User, BarChart3, Terminal } from 'lucide-react';
import { useInsightStore } from '../../stores/insightStore';
import { ContextTab } from './ContextTab';
import { UserTab } from './UserTab';
import { ScoresTab } from './ScoresTab';
import { ApiTab } from './ApiTab';

const tabs = [
  { id: 'context' as const, label: 'Context', icon: Layers },
  { id: 'user' as const, label: 'User', icon: User },
  { id: 'scores' as const, label: 'Scores', icon: BarChart3 },
  { id: 'api' as const, label: 'API', icon: Terminal },
];

export function InsightPanel() {
  const { activeTab, setActiveTab } = useInsightStore();

  return (
    <div className="w-[350px] shrink-0 bg-surface border-l border-muted-dark/30 flex flex-col">
      {/* Tab Bar */}
      <div className="flex border-b border-muted-dark/30">
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-all border-b-2 ${
                isActive
                  ? 'text-accent-blue border-accent-blue'
                  : 'text-muted border-transparent hover:text-muted-light hover:bg-surface-hover/30'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === 'context' && <ContextTab />}
        {activeTab === 'user' && <UserTab />}
        {activeTab === 'scores' && <ScoresTab />}
        {activeTab === 'api' && <ApiTab />}
      </div>
    </div>
  );
}
