import { clsx } from 'clsx';

interface ProgressBarProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'blue' | 'red' | 'amber' | 'green' | 'purple';
  showLabel?: boolean;
  className?: string;
}

const variantColors = {
  blue: 'from-accent-blue to-accent-cyan',
  red: 'from-risk-critical to-risk-high',
  amber: 'from-risk-medium to-risk-high',
  green: 'from-risk-low to-accent-cyan',
  purple: 'from-accent-purple to-accent-blue',
};

const sizes = {
  sm: 'h-1.5',
  md: 'h-2.5',
  lg: 'h-4',
};

export function ProgressBar({ value, max = 100, size = 'md', variant = 'blue', showLabel = false, className }: ProgressBarProps) {
  const percentage = Math.min(Math.round((value / max) * 100), 100);

  return (
    <div className={clsx('flex flex-col gap-1', className)}>
      {showLabel && (
        <div className="flex justify-between text-caption">
          <span className="text-text-secondary">进度</span>
          <span className="text-text-primary font-mono">{percentage}%</span>
        </div>
      )}
      <div className={clsx('w-full rounded-full bg-bg-tertiary overflow-hidden', sizes[size])}>
        <div
          className={clsx('h-full rounded-full bg-gradient-to-r transition-all duration-500 ease-out', variantColors[variant], sizes[size])}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}