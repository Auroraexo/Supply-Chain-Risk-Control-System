import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import { clsx } from 'clsx';

interface StatePanelProps {
  title: string;
  description: string;
  onRetry?: () => void;
  compact?: boolean;
  className?: string;
}

export function StatePanel({ title, description, onRetry, compact = false, className }: StatePanelProps) {
  return (
    <div className={clsx('rounded-card border border-risk-high/25 bg-risk-high/5 text-center', compact ? 'p-5' : 'p-8', className)}>
      <AlertTriangle className="mx-auto text-risk-high" size={24} />
      <p className="mt-3 text-body font-semibold text-text-primary">{title}</p>
      <p className="mt-1 text-caption text-text-secondary">{description}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          <RefreshCw size={14} />
          重新加载
        </Button>
      )}
    </div>
  );
}
