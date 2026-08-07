import { clsx } from 'clsx';
import type { RiskLevel } from '@/types/models';

interface RiskLevelBadgeProps {
  level: RiskLevel;
  size?: 'sm' | 'md';
}

const levelConfig: Record<RiskLevel, { label: string; className: string }> = {
  critical: { label: '严重', className: 'bg-risk-critical/15 text-risk-critical border-risk-critical/30' },
  high: { label: '高风险', className: 'bg-risk-high/15 text-risk-high border-risk-high/30' },
  medium: { label: '中风险', className: 'bg-risk-medium/15 text-risk-medium border-risk-medium/30' },
  low: { label: '低风险', className: 'bg-risk-low/15 text-risk-low border-risk-low/30' },
  none: { label: '无风险', className: 'bg-risk-none/15 text-risk-none border-risk-none/30' },
};

export function RiskLevelBadge({ level, size = 'md' }: RiskLevelBadgeProps) {
  const config = levelConfig[level];
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        config.className,
        size === 'sm' ? 'px-2 py-0.5 text-caption' : 'px-3 py-1 text-body'
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {config.label}
    </span>
  );
}