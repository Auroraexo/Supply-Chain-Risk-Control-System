import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';
import { clsx } from 'clsx';

interface EmptyProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
  className?: string;
}

export default function Empty({
  title = '暂无数据',
  description,
  icon = <Inbox size={24} />,
  action,
  compact = false,
  className,
}: EmptyProps) {
  return (
    <div className={clsx('flex flex-col items-center justify-center text-center', compact ? 'py-8' : 'py-14', className)}>
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-bg-tertiary/60 text-text-muted">
        {icon}
      </div>
      <p className="text-body font-semibold text-text-primary">{title}</p>
      {description && <p className="mt-1 max-w-md text-caption text-text-secondary">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
