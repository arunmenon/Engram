import { useEffect } from 'react';
import { useDynamicSimStore } from '../stores/dynamicSimStore';

/**
 * Timer hook that fires between dynamic simulation turns.
 * When auto-playing and status is 'waiting', triggers the next turn after delay.
 */
export function useDynamicPlayback() {
  const isAutoPlaying = useDynamicSimStore(s => s.isAutoPlaying);
  const status = useDynamicSimStore(s => s.status);
  const turnDelayMs = useDynamicSimStore(s => s.turnDelayMs);

  useEffect(() => {
    if (!isAutoPlaying || status !== 'waiting') return;

    const timer = setTimeout(() => {
      useDynamicSimStore.getState().generateNextTurn();
    }, turnDelayMs);

    return () => clearTimeout(timer);
  }, [isAutoPlaying, status, turnDelayMs]);
}
