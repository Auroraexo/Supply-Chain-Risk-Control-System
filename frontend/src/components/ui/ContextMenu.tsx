import { useEffect, useRef, useCallback } from 'react';
import { clsx } from 'clsx';

interface ContextMenuItem {
  label?: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  danger?: boolean;
  disabled?: boolean;
  divider?: boolean;
}

interface ContextMenuProps {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export function ContextMenu({ x, y, items, onClose }: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  const handleClickOutside = useCallback(
    (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('contextmenu', onClose);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('contextmenu', onClose);
    };
  }, [handleClickOutside, onClose]);

  // 调整位置防止溢出屏幕
  const adjustedX = Math.min(x, window.innerWidth - 200);
  const adjustedY = Math.min(y, window.innerHeight - items.length * 40 - 20);

  return (
    <div
      ref={menuRef}
      className="fixed z-50 min-w-[180px] py-1 rounded-card bg-bg-secondary border border-border shadow-2xl animate-fade-in"
      style={{ left: adjustedX, top: adjustedY }}
    >
      {items.map((item, i) => (
        <div key={i}>
          {item.divider ? (
            <div className="my-1 border-t border-border/30" />
          ) : (
            <button
              onClick={() => {
                if (!item.disabled && item.onClick) {
                  item.onClick();
                  onClose();
                }
              }}
              disabled={item.disabled}
              className={clsx(
                'w-full flex items-center gap-2.5 px-4 py-2 text-body transition-colors',
                item.danger
                  ? 'text-risk-critical hover:bg-risk-critical/10'
                  : 'text-text-primary hover:bg-bg-tertiary/50',
                item.disabled && 'opacity-40 cursor-not-allowed'
              )}
            >
              {item.icon && <span className="flex-shrink-0">{item.icon}</span>}
              {item.label}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}