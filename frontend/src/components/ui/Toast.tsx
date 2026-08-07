import { useEffect, useCallback } from 'react';
import { clsx } from 'clsx';
import { X } from 'lucide-react';
import { useToastStore } from '@/stores/toastStore';
import type { ToastType } from '@/types/common';

const typeStyles: Record<ToastType, string> = {
  success: 'border-l-risk-low bg-bg-secondary',
  error: 'border-l-risk-critical bg-bg-secondary',
  warning: 'border-l-risk-medium bg-bg-secondary',
  info: 'border-l-accent-blue bg-bg-secondary',
};

const typeIcons: Record<ToastType, string> = {
  success: '✓',
  error: '✕',
  warning: '!',
  info: 'i',
};

const typeIconStyles: Record<ToastType, string> = {
  success: 'text-risk-low',
  error: 'text-risk-critical',
  warning: 'text-risk-medium',
  info: 'text-accent-blue',
};

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        const toast = useToastStore.getState().toasts;
        if (toast.length > 0) removeToast(toast[toast.length - 1].id);
      }
    },
    [removeToast]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast, index) => (
        <div
          key={toast.id}
          className={clsx(
            'pointer-events-auto rounded-btn border-l-4 p-4 shadow-lg animate-slide-in-right',
            'flex items-start gap-3',
            typeStyles[toast.type]
          )}
          style={{ animationDelay: `${index * 50}ms` }}
        >
          <span
            className={clsx(
              'flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold',
              typeIconStyles[toast.type],
              'bg-opacity-20'
            )}
            style={{ backgroundColor: 'currentColor' }}
          >
            <span className="text-bg-primary">{typeIcons[toast.type]}</span>
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-body font-medium text-text-primary">{toast.title}</p>
            {toast.message && <p className="text-caption text-text-secondary mt-1">{toast.message}</p>}
          </div>
          <button
            onClick={() => removeToast(toast.id)}
            className="flex-shrink-0 text-text-muted hover:text-text-primary transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}