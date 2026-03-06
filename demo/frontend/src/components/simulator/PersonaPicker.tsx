import { useState } from 'react';
import { Users, ChevronRight, Sparkles } from 'lucide-react';
import {
  presetPairs,
  customerPersonas,
  supportPersonas,
  type Persona,
  type PersonaPair,
} from '../../data/personas';
import { useDynamicSimStore } from '../../stores/dynamicSimStore';

export function PersonaPicker() {
  const selectPersonas = useDynamicSimStore(s => s.selectPersonas);
  const [mode, setMode] = useState<'presets' | 'custom'>('presets');
  const [selectedCustomer, setSelectedCustomer] = useState<Persona>(customerPersonas[0]);
  const [selectedSupport, setSelectedSupport] = useState<Persona>(supportPersonas[0]);
  const [topic, setTopic] = useState(customerPersonas[0].topicSeeds[0] ?? '');
  const [maxTurns, setMaxTurns] = useState(20);

  const handlePresetSelect = (pair: PersonaPair) => {
    selectPersonas(pair.customer, pair.support, pair.defaultTopicSeed, maxTurns);
  };

  const handleCustomStart = () => {
    if (!topic.trim()) return;
    selectPersonas(selectedCustomer, selectedSupport, topic, maxTurns);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-4 h-4 text-accent-purple" />
        <h2 className="text-sm font-semibold text-gray-100">Dynamic Conversation</h2>
      </div>

      <p className="text-xs text-muted mb-4">
        Two AI personas will converse in real-time, with each message flowing through the Engram pipeline.
      </p>

      {/* Mode toggle */}
      <div className="flex items-center gap-1 bg-surface-hover rounded-full p-0.5 mb-4">
        <button
          onClick={() => setMode('presets')}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            mode === 'presets' ? 'bg-accent-purple text-white' : 'text-muted-light hover:text-gray-200'
          }`}
          aria-label="Quick start presets"
        >
          Quick Start
        </button>
        <button
          onClick={() => setMode('custom')}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            mode === 'custom' ? 'bg-accent-purple text-white' : 'text-muted-light hover:text-gray-200'
          }`}
          aria-label="Mix and match personas"
        >
          Mix &amp; Match
        </button>
      </div>

      {/* Shared settings */}
      <div className="flex items-center gap-2 mb-3">
        <label className="text-[10px] font-semibold text-muted uppercase tracking-wider">
          Max Turns
        </label>
        <input
          type="number"
          value={maxTurns}
          onChange={(e) => setMaxTurns(Math.max(2, Math.min(50, parseInt(e.target.value) || 20)))}
          className="w-16 px-2 py-1 rounded bg-surface-hover border border-muted-dark/20 text-xs text-gray-200 focus:outline-none focus:border-accent-purple/50"
          min={2}
          max={50}
          aria-label="Maximum conversation turns"
        />
      </div>

      {mode === 'presets' ? (
        <div className="space-y-2">
          {presetPairs.map(pair => (
            <button
              key={pair.id}
              onClick={() => handlePresetSelect(pair)}
              className="w-full text-left p-3 rounded-lg bg-surface-hover hover:bg-surface-card border border-muted-dark/20 hover:border-accent-purple/30 transition-all group"
              aria-label={`Select ${pair.title} scenario`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-gray-100 group-hover:text-accent-purple transition-colors">
                  {pair.title}
                </span>
                <ChevronRight className="w-3.5 h-3.5 text-muted group-hover:text-accent-purple transition-colors" />
              </div>
              <p className="text-[10px] text-muted mb-2">{pair.description}</p>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white"
                    style={{ backgroundColor: pair.customer.color }}
                  >
                    {pair.customer.avatar}
                  </div>
                  <span className="text-[9px] text-muted-light">{pair.customer.name}</span>
                </div>
                <span className="text-[9px] text-muted">vs</span>
                <div className="flex items-center gap-1">
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white"
                    style={{ backgroundColor: pair.support.color }}
                  >
                    {pair.support.avatar}
                  </div>
                  <span className="text-[9px] text-muted-light">{pair.support.name}</span>
                </div>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {/* Customer selector */}
          <div>
            <label className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-1 block">
              Customer
            </label>
            <div className="grid grid-cols-3 gap-1">
              {customerPersonas.map(p => (
                <button
                  key={p.id}
                  onClick={() => {
                    setSelectedCustomer(p);
                    if (p.topicSeeds[0]) setTopic(p.topicSeeds[0]);
                  }}
                  className={`p-2 rounded-lg text-center border transition-all ${
                    selectedCustomer.id === p.id
                      ? 'border-accent-purple bg-accent-purple/10'
                      : 'border-muted-dark/20 bg-surface-hover hover:border-muted-dark/40'
                  }`}
                  aria-label={`Select ${p.name}`}
                >
                  <div
                    className="w-7 h-7 rounded-full mx-auto mb-1 flex items-center justify-center text-[10px] font-bold text-white"
                    style={{ backgroundColor: p.color }}
                  >
                    {p.avatar}
                  </div>
                  <div className="text-[9px] text-gray-200 truncate">{p.name}</div>
                  <div className="text-[7px] text-muted truncate" title={p.description}>{p.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Support selector */}
          <div>
            <label className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-1 block">
              Support Agent
            </label>
            <div className="grid grid-cols-3 gap-1">
              {supportPersonas.map(p => (
                <button
                  key={p.id}
                  onClick={() => setSelectedSupport(p)}
                  className={`p-2 rounded-lg text-center border transition-all ${
                    selectedSupport.id === p.id
                      ? 'border-accent-purple bg-accent-purple/10'
                      : 'border-muted-dark/20 bg-surface-hover hover:border-muted-dark/40'
                  }`}
                  aria-label={`Select ${p.name}`}
                >
                  <div
                    className="w-7 h-7 rounded-full mx-auto mb-1 flex items-center justify-center text-[10px] font-bold text-white"
                    style={{ backgroundColor: p.color }}
                  >
                    {p.avatar}
                  </div>
                  <div className="text-[9px] text-gray-200 truncate">{p.name}</div>
                  <div className="text-[7px] text-muted truncate" title={p.description}>{p.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Topic input */}
          <div>
            <label className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-1 block">
              Topic / Opening Issue
            </label>
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Describe the customer's issue..."
              className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-muted-dark/20 text-xs text-gray-200 placeholder-muted resize-none focus:outline-none focus:border-accent-purple/50"
              rows={2}
            />
          </div>

          {/* Start button */}
          <button
            onClick={handleCustomStart}
            disabled={!topic.trim()}
            className="w-full py-2 rounded-lg bg-accent-purple text-white text-xs font-semibold hover:bg-accent-purple/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            aria-label="Start conversation"
          >
            <Users className="w-3.5 h-3.5" />
            Start Conversation
          </button>
        </div>
      )}
    </div>
  );
}
