import { useState } from 'react';
import {
  Play, Pause, ChevronRight, Square,
  RotateCcw, Trash2, RefreshCw, Zap,
  AlertTriangle, CheckCircle,
} from 'lucide-react';
import { useDynamicSimStore } from '../../stores/dynamicSimStore';

const DELAY_OPTIONS = [1000, 1500, 2000, 3000];

export function DynamicControls() {
  const status = useDynamicSimStore(s => s.status);
  const turnCount = useDynamicSimStore(s => s.turnCount);
  const maxTurns = useDynamicSimStore(s => s.maxTurns);
  const isAutoPlaying = useDynamicSimStore(s => s.isAutoPlaying);
  const turnDelayMs = useDynamicSimStore(s => s.turnDelayMs);
  const backendConnected = useDynamicSimStore(s => s.backendConnected);
  const lastApiError = useDynamicSimStore(s => s.lastApiError);
  const isClearing = useDynamicSimStore(s => s.isClearing);
  const isReconsolidating = useDynamicSimStore(s => s.isReconsolidating);
  const pipelineStats = useDynamicSimStore(s => s.pipelineStats);
  const ingestedEvents = useDynamicSimStore(s => s.ingestedEvents);
  const customerPersona = useDynamicSimStore(s => s.customerPersona);
  const supportPersona = useDynamicSimStore(s => s.supportPersona);

  const generateNextTurn = useDynamicSimStore(s => s.generateNextTurn);
  const startAutoPlay = useDynamicSimStore(s => s.startAutoPlay);
  const pauseAutoPlay = useDynamicSimStore(s => s.pauseAutoPlay);
  const endSession = useDynamicSimStore(s => s.endSession);
  const setTurnDelay = useDynamicSimStore(s => s.setTurnDelay);
  const reset = useDynamicSimStore(s => s.reset);
  const clearContextGraph = useDynamicSimStore(s => s.clearContextGraph);
  const triggerReconsolidate = useDynamicSimStore(s => s.triggerReconsolidate);
  const refreshPipelineStats = useDynamicSimStore(s => s.refreshPipelineStats);

  const [confirmClear, setConfirmClear] = useState(false);

  if (status === 'picking') return null;

  const nc = pipelineStats.nodeCounts;
  const isGenerating = status === 'generating' || status === 'ingesting';
  const isComplete = status === 'complete';
  const currentSpeaker = turnCount % 2 === 0 ? customerPersona : supportPersona;

  return (
    <div className="border-t border-muted-dark/30 bg-surface-dark/80 backdrop-blur-sm">
      {/* Status bar */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-muted-dark/20">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Backend badge */}
          <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium ${
            backendConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {backendConnected ? (
              <><CheckCircle className="w-2.5 h-2.5" /> Engram Live</>
            ) : (
              <><AlertTriangle className="w-2.5 h-2.5" /> Backend Offline</>
            )}
          </div>

          {/* Node counts */}
          {backendConnected && pipelineStats.totalNodes > 0 && (
            <div className="flex items-center gap-1.5 text-[9px] font-mono">
              {nc['Event'] ? <span className="text-blue-400">{nc['Event']}E</span> : null}
              {nc['Entity'] ? <span className="text-teal-400">{nc['Entity']}Ent</span> : null}
              {nc['Summary'] ? <span className="text-gray-400">{nc['Summary']}Sum</span> : null}
              {nc['UserProfile'] ? <span className="text-purple-400">{nc['UserProfile']}Prof</span> : null}
              <span className="text-muted">({pipelineStats.totalNodes}n/{pipelineStats.totalEdges}e)</span>
            </div>
          )}

          {ingestedEvents > 0 && (
            <span className="text-[9px] text-green-400/70 font-mono">{ingestedEvents} ingested</span>
          )}

          {lastApiError && (
            <>
              <span className="text-[9px] text-red-400/70 truncate max-w-[200px]" title={lastApiError}>
                {lastApiError}
              </span>
              {status === 'error' && (
                <button
                  onClick={() => {
                    useDynamicSimStore.setState({ status: 'paused', lastApiError: null });
                  }}
                  className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark"
                  aria-label="Dismiss error and retry"
                >
                  Retry
                </button>
              )}
            </>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          <button
            onClick={refreshPipelineStats}
            disabled={!backendConnected}
            className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark"
            aria-label="Refresh pipeline statistics"
          >
            <RefreshCw className="w-2.5 h-2.5" /> Stats
          </button>
          <button
            onClick={triggerReconsolidate}
            disabled={!backendConnected || isReconsolidating || pipelineStats.totalNodes === 0}
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark ${
              backendConnected && !isReconsolidating
                ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                : 'bg-gray-500/10 text-gray-600 cursor-not-allowed'
            }`}
            aria-label={isReconsolidating ? 'Consolidating' : 'Trigger consolidation'}
          >
            <Zap className={`w-2.5 h-2.5 ${isReconsolidating ? 'animate-pulse' : ''}`} />
            {isReconsolidating ? 'Consolidating...' : 'Consolidate'}
          </button>
          {confirmClear ? (
            <div className="flex items-center gap-0.5">
              <span className="text-[9px] text-red-400">Confirm?</span>
              <button
                onClick={() => { clearContextGraph(); setConfirmClear(false); }}
                className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-red-500/30 text-red-400 hover:bg-red-500/40 transition-colors focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark"
                aria-label="Confirm clear graph"
              >
                Yes
              </button>
              <button
                onClick={() => setConfirmClear(false)}
                className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-surface-hover text-muted hover:text-gray-200 transition-colors focus-visible:ring-2 focus-visible:ring-accent-purple focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark"
                aria-label="Cancel clear graph"
              >
                No
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmClear(true)}
              disabled={isClearing || !backendConnected}
              className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium transition-colors focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark ${
                backendConnected ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30' : 'bg-gray-500/10 text-gray-600 cursor-not-allowed'
              }`}
              aria-label="Clear context graph"
            >
              <Trash2 className={`w-2.5 h-2.5 ${isClearing ? 'animate-spin' : ''}`} />
              {isClearing ? 'Clearing...' : 'Clear Graph'}
            </button>
          )}
        </div>
      </div>

      {/* Controls row */}
      <div className="flex items-center justify-between px-3 py-2">
        {/* Left: Turn info */}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[10px] font-mono text-muted tabular-nums">
            Turn {turnCount}/{maxTurns}
          </span>
          {currentSpeaker && !isComplete && (
            <span className="text-[10px] text-muted-light flex items-center gap-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ backgroundColor: currentSpeaker.color }} />
              {isGenerating ? `${currentSpeaker.name}...` : `Next: ${currentSpeaker.name}`}
            </span>
          )}
          {isComplete && <span className="text-[10px] text-green-400">Session complete</span>}
        </div>

        {/* Center: Transport */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => isAutoPlaying ? pauseAutoPlay() : startAutoPlay()}
            disabled={!backendConnected || isComplete}
            className="p-1.5 rounded-full bg-accent-purple/20 text-accent-purple hover:bg-accent-purple/30 transition-colors disabled:opacity-30 focus-visible:ring-2 focus-visible:ring-accent-purple focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark"
            aria-label={isAutoPlaying ? 'Pause auto-play' : 'Start auto-play'}
          >
            {isAutoPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={generateNextTurn}
            disabled={!backendConnected || isGenerating || isComplete}
            className="p-1 rounded text-muted hover:text-gray-200 hover:bg-surface-hover transition-colors disabled:opacity-30 flex items-center gap-0.5 focus-visible:ring-2 focus-visible:ring-accent-purple focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark"
            aria-label="Generate next turn"
          >
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-[9px]">Step</span>
          </button>
          <button
            onClick={endSession}
            disabled={!backendConnected || isComplete || turnCount === 0}
            className="p-1 rounded text-muted hover:text-red-400 hover:bg-surface-hover transition-colors disabled:opacity-30 flex items-center gap-0.5 focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark"
            aria-label="End session"
          >
            <Square className="w-3 h-3" />
            <span className="text-[9px]">End</span>
          </button>
        </div>

        {/* Right: Delay + Reset */}
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-muted">Delay:</span>
          <div className="flex items-center gap-0.5 bg-surface-hover rounded-full p-0.5">
            {DELAY_OPTIONS.map(d => (
              <button
                key={d}
                onClick={() => setTurnDelay(d)}
                className={`px-1.5 py-0.5 rounded-full text-[9px] font-medium transition-colors focus-visible:ring-2 focus-visible:ring-accent-purple focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark ${
                  turnDelayMs === d ? 'bg-accent-purple text-white' : 'text-muted hover:text-gray-200'
                }`}
                aria-label={`Set turn delay to ${d / 1000} seconds`}
              >
                {d / 1000}s
              </button>
            ))}
          </div>
          <button
            onClick={reset}
            className="p-1 rounded text-muted hover:text-gray-200 hover:bg-surface-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent-purple focus-visible:ring-offset-1 focus-visible:ring-offset-surface-dark"
            aria-label="Back to persona picker"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
