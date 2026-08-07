import { type InputHTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-caption font-medium text-text-secondary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={clsx(
            'rounded-input px-3 py-2 text-body bg-bg-primary border',
            'text-text-primary placeholder:text-text-muted',
            'transition-colors duration-200',
            'focus:outline-none focus:ring-2 focus:ring-accent-blue/50 focus:border-accent-blue',
            error ? 'border-risk-critical' : 'border-border hover:border-border-light',
            className
          )}
          {...props}
        />
        {error && <p className="text-caption text-risk-critical">{error}</p>}
        {helperText && !error && <p className="text-caption text-text-muted">{helperText}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';