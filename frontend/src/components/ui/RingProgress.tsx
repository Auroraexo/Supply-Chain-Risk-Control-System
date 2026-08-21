interface RingProgressProps {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  trackColor?: string;
  label?: string;
  sublabel?: string;
  className?: string;
}

export function RingProgress({
  value,
  max = 100,
  size = 80,
  strokeWidth = 6,
  color = '#3B82F6',
  trackColor = '#334155',
  label,
  sublabel,
  className,
}: RingProgressProps) {
  const percentage = Math.min(Math.round((value / max) * 100), 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className={className}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* 渐变定义 */}
        <defs>
          <linearGradient id={`ring-grad-${color.replace('#', '')}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={color} stopOpacity="0.8" />
            <stop offset="100%" stopColor={color} stopOpacity="1" />
          </linearGradient>
        </defs>
        {/* 背景轨道 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />
        {/* 进度弧 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#ring-grad-${color.replace('#', '')})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      {/* 中心文字 */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {label && <span className="text-caption text-text-muted">{label}</span>}
        <span className="text-body font-mono font-bold text-text-primary">{percentage}%</span>
        {sublabel && <span className="text-caption text-text-muted">{sublabel}</span>}
      </div>
    </div>
  );
}