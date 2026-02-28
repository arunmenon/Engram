interface ConfidenceBarProps {
  value: number;
  className?: string;
}

export function ConfidenceBar({ value, className = '' }: ConfidenceBarProps) {
  const color = value > 0.7 ? 'bg-accent-green' : value > 0.4 ? 'bg-accent-orange' : 'bg-accent-red';

  return (
    <div className={`w-full h-1.5 rounded-full bg-surface-darker overflow-hidden ${className}`}>
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${value * 100}%` }}
      />
    </div>
  );
}
