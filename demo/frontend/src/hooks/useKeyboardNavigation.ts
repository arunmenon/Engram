import { useEffect } from 'react';
import { useSessionStore } from '../stores/sessionStore';

export function useKeyboardNavigation() {
  const store = useSessionStore;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement).isContentEditable) return;

      const state = store.getState();

      switch (e.key) {
        case 'ArrowRight': e.preventDefault(); state.stepForward(); break;
        case 'ArrowLeft': e.preventDefault(); state.stepBackward(); break;
        case ' ': e.preventDefault(); state.isPlaying ? state.pause() : state.play(); break;
        case '1': state.setCurrentSession('session-1'); break;
        case '2': state.setCurrentSession('session-2'); break;
        case '3': state.setCurrentSession('session-3'); break;
        case 'Home': e.preventDefault(); state.skipToStart(); break;
        case 'End': e.preventDefault(); state.skipToEnd(); break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
}
