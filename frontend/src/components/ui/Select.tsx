import { type SelectHTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';
import type { SelectOption } from '@/types/common';

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: string;
  error?: string;
  options: SelectOption[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, placeholder, className, id, ...props }, ref) => {
    const selectId = id || label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={selectId} className="text-caption font-medium text-text-secondary">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={clsx(
            'rounded-input px-3 py-2 text-body bg-bg-primary border cursor-pointer',
            'text-text-primary',
            'transition-colors duration-200',
            'focus:outline-none focus:ring-2 focus:ring-accent-blue/50 focus:border-accent-blue',
            error ? 'border-risk-critical' : 'border-border hover:border-border-light',
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <p className="text-caption text-risk-critical">{error}</p>}
      </div>
    );
  }
);

Select.displayName = 'Select';