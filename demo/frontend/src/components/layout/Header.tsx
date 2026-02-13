import { useEffect } from 'react';
import { Play, Pause, Brain } from 'lucide-react';
import { useSessionStore } from '../../stores/sessionStore';

export function Header() {
  const sessions = useSessionStore(s => s.sessions);
  const currentSessionId = useSessionStore(s => s.currentSessionId);
  const setCurrentSession = useSessionStore(s => s.setCurrentSession);
  const currentSession = sessions.find(s => s.id === currentSessionId);

  const isPlaying = useSessionStore(s => s.isPlaying);
  const playbackSpeed = useSessionStore(s => s.playbackSpeed);
  const play = useSessionStore(s => s.play);
  const pause = useSessionStore(s => s.pause);
  const stepForward = useSessionStore(s => s.stepForward);

  // Auto-play timer
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      stepForward();
    }, 2000 / playbackSpeed);
    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, stepForward]);

  return (
    <header className="h-12 bg-surface-dark border-b border-muted-dark/30 flex items-center justify-between px-4 shrink-0">
      {/* Left: Logo */}
      <div className="flex items-center gap-2">
        <Brain className="w-5 h-5 text-accent-blue" />
        <span className="text-sm font-semibold tracking-tight text-gray-100">Engram</span>
        <span className="text-xs text-muted bg-surface-hover px-1.5 py-0.5 rounded">demo</span>
      </div>

      {/* Center: Session Indicator */}
      <div className="flex items-center gap-3">
        {sessions.map((session, i) => (
          <button
            key={session.id}
            onClick={() => setCurrentSession(session.id)}
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
      </div>

      {/* Right: User + Controls */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-muted-light">Sarah Chen</span>
        <div className="w-6 h-6 rounded-full bg-accent-purple/30 flex items-center justify-center text-[10px] text-accent-purple font-medium">
          SC
        </div>
        <button
          onClick={() => isPlaying ? pause() : play()}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-surface-hover text-muted-light hover:text-gray-100 hover:bg-surface-card transition-colors"
        >
          {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          {isPlaying ? 'Pause' : 'Auto-Play'}
        </button>
      </div>
    </header>
  );
}
