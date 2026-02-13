import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { mockApiCalls } from '../../data/mockApiCalls';

const methodColors: Record<string, string> = {
  GET: 'bg-accent-blue/20 text-accent-blue',
  POST: 'bg-accent-green/20 text-accent-green',
  PUT: 'bg-accent-orange/20 text-accent-orange',
  DELETE: 'bg-accent-red/20 text-accent-red',
};

const statusColors: Record<string, string> = {
  '200': 'text-accent-green',
  '201': 'text-accent-green',
  '400': 'text-accent-orange',
  '500': 'text-accent-red',
};

export function ApiTab() {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="space-y-1.5">
      <h3 className="text-sm font-medium text-gray-100 mb-3">API Call Log</h3>
      {mockApiCalls.map((call, index) => {
        const isExpanded = expandedId === call.id;
        const rowBg = index % 2 === 0 ? 'bg-surface-card' : 'bg-surface-darker/50';
        return (
          <div key={call.id} className={`rounded-lg ${rowBg} border border-muted-dark/30 overflow-hidden`}>
            <button
              onClick={() => setExpandedId(isExpanded ? null : call.id)}
              className="w-full flex items-center gap-2 p-2.5 text-left hover:bg-surface-hover transition-colors"
            >
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${methodColors[call.method]}`}>
                {call.method}
              </span>
              <span className="text-xs text-gray-200 font-mono truncate flex-1">{call.endpoint}</span>
              <span className="text-[10px] text-muted font-mono">{call.latency_ms}ms</span>
              <span className={`text-[10px] font-medium ${statusColors[String(call.status)] || 'text-muted'}`}>
                {call.status}
              </span>
              <ChevronDown className={`w-3 h-3 text-muted transition-transform ${isExpanded ? 'rotate-0' : '-rotate-90'}`} />
            </button>

            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="px-2.5 pb-2.5 space-y-2">
                    {call.request && (
                      <div>
                        <p className="text-[10px] text-muted uppercase tracking-wider mb-1">Request</p>
                        <pre className="text-[11px] text-accent-green/80 bg-surface-darker rounded p-2 overflow-x-auto font-mono leading-relaxed">
                          {JSON.stringify(call.request, null, 2)}
                        </pre>
                      </div>
                    )}
                    {call.response && (
                      <div>
                        <p className="text-[10px] text-muted uppercase tracking-wider mb-1">Response</p>
                        <pre className="text-[11px] text-accent-blue/80 bg-surface-darker rounded p-2 overflow-x-auto font-mono leading-relaxed">
                          {JSON.stringify(call.response, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
