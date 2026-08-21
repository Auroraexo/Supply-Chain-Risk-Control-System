import { clsx } from 'clsx';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'card' | 'circle' | 'table-row';
  count?: number;
  /** 交错动画：每项之间的延迟（ms），0 表示无交错 */
  stagger?: number;
}

export function Skeleton({ className, variant = 'text', count = 1, stagger = 80 }: SkeletonProps) {
  const renderItem = (i: number) => {
    const style = stagger > 0 ? { animationDelay: `${i * stagger}ms` } : undefined;

    switch (variant) {
      case 'card':
        return (
          <div key={i} className="rounded-card bg-bg-secondary border border-border p-5 animate-fade-in" style={style}>
            <div className="h-5 bg-bg-tertiary rounded w-1/3 shimmer-bg mb-4" />
            <div className="space-y-2">
              <div className="h-4 bg-bg-tertiary rounded shimmer-bg" />
              <div className="h-4 bg-bg-tertiary rounded shimmer-bg w-2/3" />
            </div>
          </div>
        );
      case 'circle':
        return (
          <div
            key={i}
            className="rounded-full bg-bg-tertiary shimmer-bg animate-fade-in"
            style={{ width: 40, height: 40, ...style }}
          />
        );
      case 'table-row':
        return (
          <div key={i} className="flex gap-4 p-3 border-b border-border/30 animate-fade-in" style={style}>
            {Array.from({ length: 4 }).map((_, j) => (
              <div key={j} className="h-4 bg-bg-tertiary rounded shimmer-bg flex-1" />
            ))}
          </div>
        );
      default:
        return (
          <div
            key={i}
            className={clsx('h-4 bg-bg-tertiary rounded shimmer-bg animate-fade-in w-full', className)}
            style={style}
          />
        );
    }
  };

  return <>{Array.from({ length: count }).map((_, i) => renderItem(i))}</>;
}