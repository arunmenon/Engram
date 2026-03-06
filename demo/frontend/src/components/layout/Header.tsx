import { useEffect, useState } from 'react';
import { Play, Pause, Brain } from 'lucide-react';
import { useSessionStore } from '../../stores/sessionStore';
import { useSimulatorStore } from '../../stores/simulatorStore';
import { useDynamicSimStore } from '../../stores/dynamicSimStore';
import { getDataMode, setDataMode, getLiveSubMode, setLiveSubMode } from '../../api/mode';
import { useSimulatorPlayback } from '../../hooks/useSimulatorPlayback';

export function Header() {
  const sessions = useSessionStore(s => s.sessions);
  const currentSessionId = useSessionStore(s => s.currentSessionId);
  const setCurrentSession = useSessionStore(s => s.setCurrentSession);
  const currentSession = sessions.find(s => s.id === currentSessionId);

  // Demo auto-play
  const demoIsPlaying = useSessionStore(s => s.isPlaying);
  const demoPlaybackSpeed = useSessionStore(s => s.playbackSpeed);
  const demoPlay = useSessionStore(s => s.play);
  const demoPause = useSessionStore(s => s.pause);

  // Simulator state
  const simStatus = useSimulatorStore(s => s.status);
  const simIsPlaying = useSimulatorStore(s => s.isPlaying);
  const simScenario = useSimulatorStore(s => s.scenario);
  const simPlay = useSimulatorStore(s => s.play);
  const simPause = useSimulatorStore(s => s.pause);
  const simCurrentSessionId = useSimulatorStore(s => s.currentSessionId);

  // Dynamic state
  const dynStatus = useDynamicSimStore(s => s.status);
  const dynIsAutoPlaying = useDynamicSimStore(s => s.isAutoPlaying);
  const dynStartAutoPlay = useDynamicSimStore(s => s.startAutoPlay);
  const dynPauseAutoPlay = useDynamicSimStore(s => s.pauseAutoPlay);

  const [mode, setMode] = useState(getDataMode());
  const [subMode, setSubMode] = useState(getLiveSubMode());
  const [healthy, setHealthy] = useState(false);

  // Drive simulator playback
  useSimulatorPlayback();

  // Health check polling in live mode
  useEffect(() => {
    if (mode !== 'live') return;
    const check = async () => {
      try {
        const r = await fetch('/v1/health');
        setHealthy(r.ok);
      } catch {
        setHealthy(false);
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, [mode]);

  // Demo auto-play timer
  useEffect(() => {
    if (!demoIsPlaying) return;
    const interval = setInterval(() => {
      useSessionStore.getState().stepForward();
    }, 2000 / demoPlaybackSpeed);
    return () => clearInterval(interval);
  }, [demoIsPlaying, demoPlaybackSpeed]);

  const isLive = mode === 'live';
  const isSimulator = isLive && subMode === 'simulator';
  const hasSimScenario = simScenario !== null && simStatus !== 'picking';

  // Get the current session for simulator or demo
  const simSession = simScenario?.sessions.find(s => s.id === simCurrentSessionId);

  return (
    <header className="h-12 bg-surface-dark border-b border-muted-dark/30 flex items-center justify-between px-4 shrink-0">
      {/* Left: Logo */}
      <div className="flex items-center gap-2">
        <Brain className="w-5 h-5 text-accent-blue" />
        <span className="text-sm font-semibold tracking-tight text-gray-100">Engram</span>
        <span className={`text-xs px-1.5 py-0.5 rounded ${
          isLive
            ? subMode === 'simulator' ? 'bg-accent-purple/20 text-accent-purple'
            : subMode === 'dynamic' ? 'bg-orange-500/20 text-orange-400'
            : 'bg-accent-green/20 text-accent-green'
            : 'bg-surface-hover text-muted'
        }`}>
          {isLive ? (subMode === 'simulator' ? 'simulator' : subMode === 'dynamic' ? 'dynamic' : 'live') : 'demo'}
        </span>
      </div>

      {/* Center: Session indicator or Simulator info */}
      <div className="flex items-center gap-3">
        {isSimulator && hasSimScenario ? (
          // Show simulator session tabs from scenario
          <>
            {simScenario!.sessions.map((session, i) => {
              const isActive = session.id === simCurrentSessionId;
              return (
                <div
                  key={session.id}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
                    isActive
                      ? 'bg-surface-hover text-gray-100 ring-1 ring-muted-dark'
                      : 'text-muted-dark/50'
                  }`}
                >
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: isActive ? session.color : '#374151' }}
                  />
                  S{i + 1}
                </div>
              );
            })}
            {simSession && (
              <span className="text-xs text-muted-light ml-2">
                {simSession.title}
              </span>
            )}
          </>
        ) : !isLive ? (
          // Demo mode session tabs
          <>
            {sessions.map((session, i) => (
              <button
                key={session.id}
                onClick={() => setCurrentSession(session.id)}
                aria-current={session.id === currentSessionId ? 'true' : undefined}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all ${
                  session.id === currentSessionId
                    ? 'bg-surface-hover text-gray-100 ring-1 ring-muted-dark'
                    : 'text-muted hover:text-muted-light hover:bg-surface-hover/50'
                }`}
              >
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: session.color }} />
                S{i + 1}
              </button>
            ))}
            {currentSession && (
              <span className="text-xs text-muted-light ml-2">
                {currentSession.title}
              </span>
            )}
          </>
        ) : null}
      </div>

      {/* Right: Mode Toggle + Sub-mode toggle + Controls */}
      <div className="flex items-center gap-3">
        {/* Demo / Live toggle pill */}
        <div className="flex items-center gap-1 bg-surface-hover rounded-full p-0.5">
          <button
            onClick={() => { setDataMode('mock'); setMode('mock'); window.location.reload(); }}
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition-colors ${
              mode === 'mock' ? 'bg-accent-blue text-white' : 'text-muted-light hover:text-gray-200'
            }`}
          >
            Demo
          </button>
          <button
            onClick={() => { setDataMode('live'); setMode('live'); window.location.reload(); }}
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition-colors ${
              mode === 'live' ? 'bg-accent-green text-white' : 'text-muted-light hover:text-gray-200'
            }`}
          >
            Live
          </button>
        </div>

        {/* Live sub-mode toggle: Interactive / Simulator */}
        {isLive && (
          <div className="flex items-center gap-1 bg-surface-hover rounded-full p-0.5">
            <button
              onClick={() => { setLiveSubMode('interactive'); setSubMode('interactive'); window.location.reload(); }}
              className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition-colors ${
                subMode === 'interactive' ? 'bg-accent-green text-white' : 'text-muted-light hover:text-gray-200'
              }`}
            >
              Interactive
            </button>
            <button
              onClick={() => { setLiveSubMode('simulator'); setSubMode('simulator'); window.location.reload(); }}
              className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition-colors ${
                subMode === 'simulator' ? 'bg-accent-purple text-white' : 'text-muted-light hover:text-gray-200'
              }`}
            >
              Simulator
            </button>
            <button
              onClick={() => { setLiveSubMode('dynamic'); setSubMode('dynamic'); window.location.reload(); }}
              className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition-colors ${
                subMode === 'dynamic' ? 'bg-orange-500 text-white' : 'text-muted-light hover:text-gray-200'
              }`}
            >
              Dynamic
            </button>
          </div>
        )}

        {isLive && !isSimulator && (
          <div
            className={`w-2 h-2 rounded-full ${healthy ? 'bg-green-400' : 'bg-red-400'}`}
            title={healthy ? 'Backend healthy' : 'Backend unreachable'}
          />
        )}

        {/* User avatar */}
        <span className="text-xs text-muted-light">Sarah Chen</span>
        <div className="w-6 h-6 rounded-full bg-accent-purple/30 flex items-center justify-center text-[10px] text-accent-purple font-medium">
          SC
        </div>

        {/* Play/Pause: for demo mode only (simulator has its own controls) */}
        {!isLive && (
          <button
            onClick={() => demoIsPlaying ? demoPause() : demoPlay()}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-surface-hover text-muted-light hover:text-gray-100 hover:bg-surface-card transition-colors"
          >
            {demoIsPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
            {demoIsPlaying ? 'Pause' : 'Auto-Play'}
          </button>
        )}

        {/* Dynamic mode quick play button */}
        {subMode === 'dynamic' && isLive && dynStatus !== 'picking' && (
          <button
            onClick={() => dynIsAutoPlaying ? dynPauseAutoPlay() : dynStartAutoPlay()}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-orange-500/20 text-orange-400 hover:bg-orange-500/30 transition-colors"
          >
            {dynIsAutoPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
            {dynIsAutoPlaying ? 'Pause' : 'Play'}
          </button>
        )}

        {/* Simulator quick play button in header */}
        {isSimulator && hasSimScenario && (
          <button
            onClick={() => simIsPlaying ? simPause() : simPlay()}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-accent-purple/20 text-accent-purple hover:bg-accent-purple/30 transition-colors"
          >
            {simIsPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
            {simIsPlaying ? 'Pause' : 'Play'}
          </button>
        )}
      </div>
    </header>
  );
}
