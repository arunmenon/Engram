import { useEffect } from 'react';
import { useSimulatorStore } from '../stores/simulatorStore';

/**
 * Timer hook that drives simulator auto-play.
 * Call this once in a top-level component (e.g., Header or SimulatorControls).
 */
export function useSimulatorPlayback() {
  const isPlaying = useSimulatorStore(s => s.isPlaying);
  const speed = useSimulatorStore(s => s.playbackSpeed);

  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      useSimulatorStore.getState().stepForward();
    }, 2000 / speed);
    return () => clearInterval(interval);
  }, [isPlaying, speed]);
}
