import { useEffect, useRef } from 'react';
import { useSessionStore } from '../stores/sessionStore';
import { useGraphStore } from '../stores/graphStore';

export function usePlaybackUrl() {
  const currentSessionId = useSessionStore((s) => s.currentSessionId);
  const currentStepIndex = useSessionStore((s) => s.currentStepIndex);
  const playbackSpeed = useSessionStore((s) => s.playbackSpeed);
  const layoutType = useGraphStore((s) => s.layoutType);
  const initialized = useRef(false);

  // Restore state from URL hash on mount
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const hash = window.location.hash.slice(1);
    if (!hash) return;

    const params = new URLSearchParams(hash);
    const session = params.get('session');
    const step = params.get('step');
    const speed = params.get('speed');
    const layout = params.get('layout');

    if (session) useSessionStore.getState().setCurrentSession(session);
    if (step) {
      const stepNum = parseInt(step, 10);
      if (!isNaN(stepNum) && stepNum >= 0) useSessionStore.getState().goToStep(stepNum);
    }
    if (speed) {
      const speedNum = parseInt(speed, 10);
      if ([1, 2, 5].includes(speedNum)) useSessionStore.getState().setPlaybackSpeed(speedNum);
    }
    if (layout === 'force' || layout === 'circular') {
      useGraphStore.getState().setLayoutType(layout);
    }
  }, []);

  // Update hash when state changes (debounced)
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    if (!initialized.current) return;

    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      const params = new URLSearchParams();
      params.set('session', currentSessionId);
      if (currentStepIndex >= 0) params.set('step', String(currentStepIndex));
      params.set('speed', String(playbackSpeed));
      params.set('layout', layoutType);
      window.location.hash = params.toString();
    }, 300);

    return () => clearTimeout(timeoutRef.current);
  }, [currentSessionId, currentStepIndex, playbackSpeed, layoutType]);
}
