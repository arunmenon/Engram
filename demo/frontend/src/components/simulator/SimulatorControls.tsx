import {
  Play, Pause, SkipBack, SkipForward, ChevronLeft, ChevronRight,
  RotateCcw, Trash2, RefreshCw, Zap, AlertTriangle, CheckCircle, Loader2
} from 'lucide-react';
import { useSimulatorStore } from '../../stores/simulatorStore';

const SPEED_OPTIONS = [0.5, 1, 2, 3];

export function SimulatorControls() {
  const status = useSimulatorStore(s => s.status);
  const scenario = useSimulatorStore(s => s.scenario);
  const currentStepIndex = useSimulatorStore(s => s.currentStepIndex);
  const isPlaying = useSimulatorStore(s => s.isPlaying);
  const playbackSpeed = useSimulatorStore(s => s.playbackSpeed);
  const currentSessionId = useSimulatorStore(s => s.currentSessionId);
  const backendConnected = useSimulatorStore(s => s.backendConnected);
  const detecting = useSimulatorStore(s => s.detecting);
  const ingestedEvents = useSimulatorStore(s => s.ingestedEvents);
  const lastApiError = useSimulatorStore(s => s.lastApiError);
  const isClearing = useSimulatorStore(s => s.isClearing);
  const isReconsolidating = useSimulatorStore(s => s.isReconsolidating);
  const pipelineStats = useSimulatorStore(s => s.pipelineStats);
  const completedSessions = useSimulatorStore(s => s.completedSessions);

  const play = useSimulatorStore(s => s.play);
  const pause = useSimulatorStore(s => s.pause);
  const stepForward = useSimulatorStore(s => s.stepForward);
  const stepBackward = useSimulatorStore(s => s.stepBackward);
  const skipToStart = useSimulatorStore(s => s.skipToStart);
  const skipToEnd = useSimulatorStore(s => s.skipToEnd);
  const goToStep = useSimulatorStore(s => s.goToStep);
  const setPlaybackSpeed = useSimulatorStore(s => s.setPlaybackSpeed);
  const reset = useSimulatorStore(s => s.reset);
  const clearContextGraph = useSimulatorStore(s => s.clearContextGraph);
  const triggerReconsolidate = useSimulatorStore(s => s.triggerReconsolidate);
  const refreshPipelineStats = useSimulatorStore(s => s.refreshPipelineStats);

  if (!scenario || status === 'picking') return null;

  const totalSteps = scenario.messages.length;
  const displayStep = currentStepIndex + 1;
  const progress = totalSteps > 0 ? Math.max(0, (displayStep / totalSteps) * 100) : 0;

  const currentSession = scenario.sessions.find(s => s.id === currentSessionId);
  const sessionIndex = scenario.sessions.findIndex(s => s.id === currentSessionId);

  // Pipeline stats summary
  const nc = pipelineStats.nodeCounts;
  const ec = pipelineStats.edgeCounts;

  return (
    <div className="border-t border-muted-dark/30 bg-surface-dark/80 backdrop-blur-sm">
      {/* Backend status + Pipeline stats bar */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-muted-dark/20">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Backend connection badge */}
          <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium ${
            detecting
              ? 'bg-yellow-500/20 text-yellow-400'
              : backendConnected
              ? 'bg-green-500/20 text-green-400'
              : 'bg-red-500/20 text-red-400'
          }`}>
            {detecting ? (
              <><Loader2 className="w-2.5 h-2.5 animate-spin" /> Detecting…</>
            ) : backendConnected ? (
              <><CheckCircle className="w-2.5 h-2.5" /> Engram Live</>
            ) : (
              <><AlertTriangle className="w-2.5 h-2.5" /> Backend Offline</>
            )}
          </div>

          {/* Pipeline node counts */}
          {backendConnected && pipelineStats.totalNodes > 0 && (
            <div className="flex items-center gap-1.5 text-[9px] font-mono">
              {nc['Event'] ? (
                <span className="text-blue-400" title="Event nodes (Consumer 1: Projection)">
                  {nc['Event']}E
                </span>
              ) : null}
              {nc['Entity'] ? (
                <span className="text-teal-400" title="Entity nodes (Consumer 2: Extraction)">
                  {nc['Entity']}Ent
                </span>
              ) : null}
              {nc['Summary'] ? (
                <span className="text-gray-400" title="Summary nodes (Consumer 4: Consolidation)">
                  {nc['Summary']}Sum
                </span>
              ) : null}
              {nc['UserProfile'] ? (
                <span className="text-purple-400" title="UserProfile nodes (Consumer 2: Extraction)">
                  {nc['UserProfile']}Prof
                </span>
              ) : null}
              {nc['Preference'] ? (
                <span className="text-green-400" title="Preference nodes (Consumer 2: Extraction)">
                  {nc['Preference']}Pref
                </span>
              ) : null}
              {nc['Skill'] ? (
                <span className="text-purple-300" title="Skill nodes (Consumer 2: Extraction)">
                  {nc['Skill']}Skill
                </span>
              ) : null}
              {nc['BehavioralPattern'] ? (
                <span className="text-amber-400" title="Pattern nodes (Consumer 2: Extraction)">
                  {nc['BehavioralPattern']}Pat
                </span>
              ) : null}
              <span className="text-muted" title="Total nodes / edges">
                ({pipelineStats.totalNodes}n/{pipelineStats.totalEdges}e)
              </span>
            </div>
          )}

          {/* Ingested events counter */}
          {ingestedEvents > 0 && (
            <span className="text-[9px] text-green-400/70 font-mono">
              {ingestedEvents} ingested
            </span>
          )}

          {/* Completed sessions */}
          {completedSessions.length > 0 && (
            <span className="text-[9px] text-blue-400/70 font-mono">
              {completedSessions.length}/{scenario.sessions.length} sessions done
            </span>
          )}

          {/* Error message */}
          {lastApiError && (
            <span className="text-[9px] text-red-400/70 truncate max-w-[300px]" title={lastApiError}>
              {lastApiError}
            </span>
          )}
        </div>

        {/* Right: Pipeline action buttons */}
        <div className="flex items-center gap-1">
          {/* Refresh stats */}
          <button
            onClick={refreshPipelineStats}
            disabled={!backendConnected}
            className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium transition-colors bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Refresh pipeline stats from backend"
          >
            <RefreshCw className="w-2.5 h-2.5" />
            Stats
          </button>

          {/* Trigger Reconsolidate */}
          <button
            onClick={triggerReconsolidate}
            disabled={!backendConnected || isReconsolidating || pipelineStats.totalNodes === 0}
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium transition-colors ${
              backendConnected && !isReconsolidating
                ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                : 'bg-gray-500/10 text-gray-600 cursor-not-allowed'
            }`}
            title="Trigger reconsolidation (creates Summary nodes)"
          >
            <Zap className={`w-2.5 h-2.5 ${isReconsolidating ? 'animate-pulse' : ''}`} />
            {isReconsolidating ? 'Consolidating…' : 'Consolidate'}
          </button>

          {/* Clear Context Graph */}
          <button
            onClick={clearContextGraph}
            disabled={isClearing || !backendConnected}
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium transition-colors ${
              backendConnected
                ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                : 'bg-gray-500/10 text-gray-600 cursor-not-allowed'
            }`}
            title="Clear all data in context graph (destructive replay)"
          >
            <Trash2 className={`w-2.5 h-2.5 ${isClearing ? 'animate-spin' : ''}`} />
            {isClearing ? 'Clearing…' : 'Clear Graph'}
          </button>
        </div>
      </div>

      {/* Progress bar — clickable scrubber */}
      <div
        className="relative h-1.5 bg-surface-hover cursor-pointer group"
        onClick={(e) => {
          if (!backendConnected) return;
          const rect = e.currentTarget.getBoundingClientRect();
          const pct = (e.clientX - rect.left) / rect.width;
          const step = Math.round(pct * (totalSteps - 1));
          goToStep(step);
        }}
      >
        <div
          className="absolute inset-y-0 left-0 bg-accent-blue transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-accent-blue border-2 border-surface-dark opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ left: `calc(${progress}% - 6px)` }}
        />
      </div>

      {/* Controls row */}
      <div className="flex items-center justify-between px-3 py-2">
        {/* Left: Step info */}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[10px] font-mono text-muted tabular-nums">
            {displayStep > 0 ? displayStep : '—'}/{totalSteps}
          </span>
          {currentSession && (
            <span className="text-[10px] text-muted-light truncate">
              <span className="inline-block w-1.5 h-1.5 rounded-full mr-1" style={{ backgroundColor: currentSession.color }} />
              S{sessionIndex + 1}: {currentSession.title}
            </span>
          )}
        </div>

        {/* Center: Transport controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={skipToStart}
            disabled={!backendConnected}
            className="p-1 rounded text-muted hover:text-gray-200 hover:bg-surface-hover transition-colors disabled:opacity-30"
            title="Skip to start"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={stepBackward}
            disabled={currentStepIndex <= 0 || !backendConnected}
            className="p-1 rounded text-muted hover:text-gray-200 hover:bg-surface-hover transition-colors disabled:opacity-30"
            title="Step backward"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => isPlaying ? pause() : play()}
            disabled={!backendConnected}
            className="p-1.5 rounded-full bg-accent-blue/20 text-accent-blue hover:bg-accent-blue/30 transition-colors disabled:opacity-30"
            title={!backendConnected ? 'Backend required' : isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={stepForward}
            disabled={currentStepIndex >= totalSteps - 1 || !backendConnected}
            className="p-1 rounded text-muted hover:text-gray-200 hover:bg-surface-hover transition-colors disabled:opacity-30"
            title="Step forward"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={skipToEnd}
            disabled={!backendConnected}
            className="p-1 rounded text-muted hover:text-gray-200 hover:bg-surface-hover transition-colors disabled:opacity-30"
            title="Skip to end (ingest all + reconsolidate)"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Right: Speed + Reset */}
        <div className="flex items-center gap-2">
          {/* Speed selector */}
          <div className="flex items-center gap-0.5 bg-surface-hover rounded-full p-0.5">
            {SPEED_OPTIONS.map(spd => (
              <button
                key={spd}
                onClick={() => setPlaybackSpeed(spd)}
                className={`px-1.5 py-0.5 rounded-full text-[9px] font-medium transition-colors ${
                  playbackSpeed === spd
                    ? 'bg-accent-blue text-white'
                    : 'text-muted hover:text-gray-200'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>

          {/* Reset */}
          <button
            onClick={reset}
            className="p-1 rounded text-muted hover:text-gray-200 hover:bg-surface-hover transition-colors"
            title="Back to scenarios"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
