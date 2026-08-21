import { useState, useCallback, useRef } from 'react';
import { clsx } from 'clsx';
import type { TableColumn } from '@/types/common';

interface TableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  loading?: boolean;
  emptyText?: string;
  onRowClick?: (item: T) => void;
  className?: string;
  /** 启用移动端卡片视图 */
  mobileCardView?: boolean;
}

export function Table<T>({
  columns = [],
  data = [],
  keyExtractor,
  loading = false,
  emptyText = '暂无数据',
  onRowClick,
  className,
  mobileCardView = true,
}: TableProps<T>) {
  const [colWidths, setColWidths] = useState<Record<string, number>>({});
  const resizeRef = useRef<{ colKey: string; startX: number; startWidth: number } | null>(null);

  const handleResizeStart = useCallback(
    (colKey: string, e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      const startX = e.clientX;
      const startWidth = colWidths[colKey] || 150;
      resizeRef.current = { colKey, startX, startWidth };

      const handleMouseMove = (ev: MouseEvent) => {
        if (!resizeRef.current) return;
        const diff = ev.clientX - resizeRef.current.startX;
        const newWidth = Math.max(60, resizeRef.current.startWidth + diff);
        setColWidths((prev) => ({ ...prev, [resizeRef.current!.colKey]: newWidth }));
      };

      const handleMouseUp = () => {
        resizeRef.current = null;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [colWidths]
  );

  const renderSkeleton = () => (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i} className="border-b border-border/50">
          {columns.map((col, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-4 bg-bg-tertiary rounded shimmer-bg" style={{ width: `${60 + Math.random() * 30}%` }} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );

  const getValue = (item: T, col: TableColumn<T>) => {
    if (col.render) return col.render(item);
    return String((item as Record<string, unknown>)[col.key as string] ?? '');
  };

  return (
    <div className={clsx('overflow-x-auto rounded-card border border-border', className)}>
      {/* 桌面端表格 */}
      <table className="w-full hidden sm:table">
        <thead>
          <tr className="border-b border-border bg-bg-tertiary/30">
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className="relative px-4 py-3 text-left text-caption font-medium text-text-secondary uppercase tracking-wider select-none"
                style={{ width: colWidths[String(col.key)] || col.width || 'auto' }}
              >
                {col.header}
                {/* 列宽拖拽手柄 */}
                <div
                  className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-accent-blue/40 transition-colors group/resize"
                  onMouseDown={(e) => handleResizeStart(String(col.key), e)}
                >
                  <div className="w-0.5 h-full mx-auto bg-transparent group-hover/resize:bg-accent-blue/60 transition-colors" />
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            renderSkeleton()
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-text-muted">
                {emptyText}
              </td>
            </tr>
          ) : (
            data.map((item) => (
              <tr
                key={keyExtractor(item)}
                onClick={() => onRowClick?.(item)}
                className={clsx(
                  'border-b border-border/30 transition-colors',
                  onRowClick && 'cursor-pointer hover:bg-bg-tertiary/30'
                )}
              >
                {columns.map((col) => (
                  <td
                    key={String(col.key)}
                    className="px-4 py-3 text-body text-text-primary"
                    style={{ width: colWidths[String(col.key)] || col.width || 'auto' }}
                  >
                    {getValue(item, col)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* 移动端卡片视图 */}
      {mobileCardView && (
        <div className="sm:hidden divide-y divide-border/30">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="p-4 animate-fade-in" style={{ animationDelay: `${i * 80}ms` }}>
                <div className="h-5 bg-bg-tertiary rounded shimmer-bg w-1/3 mb-3" />
                <div className="space-y-2">
                  <div className="h-4 bg-bg-tertiary rounded shimmer-bg w-2/3" />
                  <div className="h-4 bg-bg-tertiary rounded shimmer-bg w-1/2" />
                </div>
              </div>
            ))
          ) : data.length === 0 ? (
            <div className="p-12 text-center text-text-muted">{emptyText}</div>
          ) : (
            data.map((item, idx) => (
              <div
                key={keyExtractor(item)}
                onClick={() => onRowClick?.(item)}
                className={clsx(
                  'p-4 animate-fade-in',
                  onRowClick && 'cursor-pointer hover:bg-bg-tertiary/20 active:bg-bg-tertiary/30 transition-colors'
                )}
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                {columns.map((col, j) => (
                  <div key={j} className="flex justify-between py-1.5">
                    <span className="text-caption text-text-muted">{col.header}</span>
                    <span className="text-caption text-text-primary text-right font-medium ml-4">{getValue(item, col)}</span>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}