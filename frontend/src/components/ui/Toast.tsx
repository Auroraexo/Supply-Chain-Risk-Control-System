import { useEffect, useCallback, useRef } from 'react';
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

const typeProgressColors: Record<ToastType, string> = {
  success: 'bg-risk-low',
  error: 'bg-risk-critical',
  warning: 'bg-risk-medium',
  info: 'bg-accent-blue',
};

function ToastItem({ toast: t, onRemove }: { toast: { id: string; type: ToastType; title: string; message?: string; duration?: number }; onRemove: (id: string) => void }) {
  const duration = t.duration || 4000;
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => onRemove(t.id), duration);
    return () => clearTimeout(timer);
  }, [t.id, duration, onRemove]);

  return (
    <div
      className={clsx(
        'pointer-events-auto rounded-btn border-l-4 shadow-lg animate-slide-in-right relative overflow-hidden',
        'flex items-start gap-3 p-4',
        typeStyles[t.type]
      )}
    >
      {/* 倒计时进度条 */}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-bg-tertiary">
        <div
          ref={progressRef}
          className={`h-full ${typeProgressColors[t.type]} transition-all`}
          style={{ width: '100%', animation: `toast-shrink ${duration}ms linear forwards` }}
        />
      </div>
      <span
        className={clsx(
          'flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold',
          typeIconStyles[t.type],
          'bg-opacity-20'
        )}
        style={{ backgroundColor: 'currentColor' }}
      >
        <span className="text-bg-primary">{typeIcons[t.type]}</span>
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-body font-medium text-text-primary">{t.title}</p>
        {t.message && <p className="text-caption text-text-secondary mt-1">{t.message}</p>}
      </div>
      <button
        onClick={() => onRemove(t.id)}
        className="flex-shrink-0 text-text-muted hover:text-text-primary transition-colors"
      >
        <X size={16} />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        const current = useToastStore.getState().toasts;
        if (current.length > 0) removeToast(current[current.length - 1].id);
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
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
      ))}
    </div>
  );
}