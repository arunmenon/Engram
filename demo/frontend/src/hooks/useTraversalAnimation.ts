import { useEffect } from 'react';
import { useAnimationStore } from '../stores/animationStore';

export function useTraversalAnimation() {
  const isAnimating = useAnimationStore((s) => s.isAnimating);
  const animationSpeed = useAnimationStore((s) => s.animationSpeed);

  useEffect(() => {
    if (!isAnimating) return;
    // Use getState() inside callbacks to avoid stale closures
    useAnimationStore.getState().stepAnimation();
    const interval = setInterval(() => {
      useAnimationStore.getState().stepAnimation();
    }, animationSpeed);
    return () => clearInterval(interval);
  }, [isAnimating, animationSpeed]);
}
