import { useMemo } from 'react';
import { SkipBack, Play, Pause, SkipForward } from 'lucide-react';
import { useSessionStore } from '../../stores/sessionStore';
import { useGraphStore } from '../../stores/graphStore';

export function SessionTimeline() {
  const sessions = useSessionStore(s => s.sessions);
  const currentSessionId = useSessionStore(s => s.currentSessionId);
  const setCurrentSession = useSessionStore(s => s.setCurrentSession);
  const allMessages = useSessionStore(s => s.messages);
  const currentStepIndex = useSessionStore(s => s.currentStepIndex);
  const autoPlayStarted = useSessionStore(s => s.autoPlayStarted);

  const isPlaying = useSessionStore(s => s.isPlaying);
  const playbackSpeed = useSessionStore(s => s.playbackSpeed);
  const play = useSessionStore(s => s.play);
  const pause = useSessionStore(s => s.pause);
  const skipToStart = useSessionStore(s => s.skipToStart);
  const skipToEnd = useSessionStore(s => s.skipToEnd);
  const setPlaybackSpeed = useSessionStore(s => s.setPlaybackSpeed);
  const goToStep = useSessionStore(s => s.goToStep);

  const nodes = useGraphStore(s => s.nodes);

  const getSessionEvents = (sessionId: string) =>
    nodes.filter(n => n.session_id === sessionId && n.node_type === 'Event');

  const getGapLabel = (endTime: string, startTime: string) => {
    const diff = new Date(startTime).getTime() - new Date(endTime).getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    if (days >= 7) return `${Math.floor(days / 7)} week${Math.floor(days / 7) > 1 ? 's' : ''}`;
    return `${days} day${days > 1 ? 's' : ''}`;
  };

  // Build a mapping from (session_id, event_index) to global message index
  const sessionMessageIndices = useMemo(() => {
    const map: Record<string, number[]> = {};
    allMessages.forEach((msg, globalIdx) => {
      if (!map[msg.session_id]) map[msg.session_id] = [];
      map[msg.session_id].push(globalIdx);
    });
    return map;
  }, [allMessages]);

  const totalEvents = nodes.filter(n => n.node_type === 'Event').length;

  return (
    <div className="h-[100px] bg-surface-dark border-t border-muted-dark/30 flex items-center px-4 gap-4">
      {/* Playback Controls */}
      <div className="flex items-center gap-1.5 shrink-0">
        <button
          onClick={skipToStart}
          className="p-1.5 rounded text-muted hover:text-muted-light hover:bg-surface-hover transition-colors"
        >
          <SkipBack className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => isPlaying ? pause() : play()}
          className="p-1.5 rounded text-muted hover:text-muted-light hover:bg-surface-hover transition-colors"
        >
          {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
        </button>
        <button
          onClick={skipToEnd}
          className="p-1.5 rounded text-muted hover:text-muted-light hover:bg-surface-hover transition-colors"
        >
          <SkipForward className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => setPlaybackSpeed(playbackSpeed === 1 ? 2 : playbackSpeed === 2 ? 5 : 1)}
          className="ml-1 px-2 py-0.5 rounded text-[10px] font-mono text-muted hover:text-muted-light bg-surface-hover transition-colors"
        >
          {playbackSpeed}x
        </button>
      </div>

      {/* Timeline Bands */}
      <div className="flex-1 flex items-center gap-0 h-16 relative">
        {sessions.map((session, i) => {
          const events = getSessionEvents(session.id);
          const isActive = session.id === currentSessionId;
          const sessionMsgIndices = sessionMessageIndices[session.id] || [];

          return (
            <div key={session.id} className="contents">
              {/* Gap between sessions */}
              {i > 0 && (
                <div className="flex items-center justify-center px-2 shrink-0">
                  <div className="flex flex-col items-center">
                    <div className="w-px h-3 bg-muted-dark/50" />
                    <span className="text-[9px] text-muted whitespace-nowrap">
                      {getGapLabel(sessions[i - 1].end_time, session.start_time)}
                    </span>
                    <div className="w-px h-3 bg-muted-dark/50" />
                  </div>
                </div>
              )}

              {/* Session Band */}
              <button
                onClick={() => setCurrentSession(session.id)}
                className={`flex-1 h-12 rounded-lg relative overflow-hidden transition-all cursor-pointer border ${
                  isActive
                    ? 'border-muted-dark/60 shadow-lg'
                    : 'border-transparent opacity-50 hover:opacity-75'
                }`}
                style={{
                  backgroundColor: `${session.color}${isActive ? '30' : '15'}`,
                }}
              >
                {/* Session Label */}
                <div className="absolute inset-0 flex items-center justify-between px-3">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: session.color }}
                    />
                    <span className="text-[11px] font-medium text-gray-200 truncate">
                      S{i + 1}: {session.title}
                    </span>
                  </div>
                  <span className="text-[10px] text-muted-light font-mono">
                    {events.length} evt
                  </span>
                </div>

                {/* Event Dots — each dot maps to a message in the session */}
                <div className="absolute bottom-1.5 left-3 right-3 flex items-center gap-1">
                  {events.map((evt, evtIdx) => {
                    const globalMsgIdx = sessionMsgIndices[evtIdx] ?? -1;
                    const isCurrentDot = autoPlayStarted && globalMsgIdx === currentStepIndex;
                    const isPastDot = autoPlayStarted && globalMsgIdx >= 0 && globalMsgIdx <= currentStepIndex;

                    return (
                      <div
                        key={evt.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (globalMsgIdx >= 0) {
                            goToStep(globalMsgIdx);
                          }
                        }}
                        className={`rounded-full cursor-pointer transition-all ${
                          isCurrentDot
                            ? 'w-2.5 h-2.5 ring-2 ring-white/60 scale-125'
                            : 'w-1.5 h-1.5'
                        }`}
                        style={{
                          backgroundColor: session.color,
                          opacity: isCurrentDot ? 1 : isPastDot ? 0.9 : isActive ? 0.8 : 0.4,
                        }}
                        title={`Event ${evtIdx + 1}`}
                      />
                    );
                  })}
                </div>
              </button>
            </div>
          );
        })}
      </div>

      {/* Right: Total + Progress */}
      <div className="shrink-0 text-right">
        <p className="text-xs text-muted-light font-mono">{totalEvents}</p>
        <p className="text-[10px] text-muted">events</p>
        {autoPlayStarted && (
          <p className="text-[9px] text-muted font-mono">
            {currentStepIndex + 1}/{allMessages.length}
          </p>
        )}
      </div>
    </div>
  );
}
