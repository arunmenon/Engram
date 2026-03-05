import { useAnnounceStore } from '../../stores/announceStore';

export function ScreenReaderAnnouncer() {
  const message = useAnnounceStore((s) => s.message);

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    >
      {message}
    </div>
  );
}
