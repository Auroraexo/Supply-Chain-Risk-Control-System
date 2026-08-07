import { clsx } from 'clsx';
import type { RiskLevel } from '@/types/models';

interface BadgeProps {
  variant?: RiskLevel | 'default' | 'info' | 'success';
  children: React.ReactNode;
  dot?: boolean;
  className?: string;
}

const badgeStyles: Record<string, string> = {
  critical: 'bg-risk-critical/15 text-risk-critical border-risk-critical/30',
  high: 'bg-risk-high/15 text-risk-high border-risk-high/30',
  medium: 'bg-risk-medium/15 text-risk-medium border-risk-medium/30',
  low: 'bg-risk-low/15 text-risk-low border-risk-low/30',
  none: 'bg-risk-none/15 text-risk-none border-risk-none/30',
  default: 'bg-bg-tertiary/50 text-text-secondary border-border',
  info: 'bg-accent-blue/15 text-accent-blue border-accent-blue/30',
  success: 'bg-risk-low/15 text-risk-low border-risk-low/30',
};

export function Badge({ variant = 'default', dot = false, className, children }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-caption font-medium border',
        badgeStyles[variant],
        className
      )}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse-dot" />}
      {children}
    </span>
  );
}