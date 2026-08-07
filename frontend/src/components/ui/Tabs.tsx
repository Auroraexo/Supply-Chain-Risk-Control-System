import { useState } from 'react';
import { clsx } from 'clsx';

interface Tab {
  key: string;
  label: string;
  count?: number;
}

interface TabsProps {
  tabs: Tab[];
  activeKey: string;
  onChange: (key: string) => void;
  className?: string;
}

export function Tabs({ tabs, activeKey, onChange, className }: TabsProps) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);

  return (
    <div className={clsx('flex gap-1 border-b border-border', className)}>
      {tabs.map((tab) => {
        const isActive = tab.key === activeKey;
        const isHovered = tab.key === hoveredKey;
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            onMouseEnter={() => setHoveredKey(tab.key)}
            onMouseLeave={() => setHoveredKey(null)}
            className={clsx(
              'relative px-4 py-2.5 text-body font-medium transition-colors duration-200',
              isActive ? 'text-accent-blue' : 'text-text-secondary hover:text-text-primary'
            )}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className={clsx(
                'ml-1.5 px-1.5 py-0.5 rounded-full text-caption',
                isActive ? 'bg-accent-blue/15 text-accent-blue' : 'bg-bg-tertiary text-text-muted'
              )}>
                {tab.count}
              </span>
            )}
            <span
              className={clsx(
                'absolute bottom-0 left-0 h-0.5 bg-accent-blue transition-all duration-200',
                isActive ? 'w-full' : isHovered ? 'w-1/2' : 'w-0'
              )}
            />
          </button>
        );
      })}
    </div>
  );
}