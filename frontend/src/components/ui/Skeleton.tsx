import { clsx } from 'clsx';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'card' | 'circle' | 'table-row';
  count?: number;
}

export function Skeleton({ className, variant = 'text', count = 1 }: SkeletonProps) {
  const renderItem = (i: number) => {
    switch (variant) {
      case 'card':
        return (
          <div key={i} className="rounded-card bg-bg-secondary border border-border p-5">
            <div className="h-5 bg-bg-tertiary rounded w-1/3 animate-pulse mb-4" />
            <div className="space-y-2">
              <div className="h-4 bg-bg-tertiary rounded animate-pulse" />
              <div className="h-4 bg-bg-tertiary rounded animate-pulse w-2/3" />
            </div>
          </div>
        );
      case 'circle':
        return <div key={i} className="rounded-full bg-bg-tertiary animate-pulse" style={{ width: 40, height: 40 }} />;
      case 'table-row':
        return (
          <div key={i} className="flex gap-4 p-3 border-b border-border/30">
            {Array.from({ length: 4 }).map((_, j) => (
              <div key={j} className="h-4 bg-bg-tertiary rounded animate-pulse flex-1" />
            ))}
          </div>
        );
      default:
        return <div key={i} className={clsx('h-4 bg-bg-tertiary rounded animate-pulse w-full', className)} />;
    }
  };

  return <>{Array.from({ length: count }).map((_, i) => renderItem(i))}</>;
}