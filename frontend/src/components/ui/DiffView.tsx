import { clsx } from 'clsx';

interface DiffViewProps {
  left: Record<string, unknown>;
  right: Record<string, unknown>;
  leftLabel?: string;
  rightLabel?: string;
  fields?: string[];
}

const FIELD_LABELS: Record<string, string> = {
  rule_name: '规则名称',
  rule_type: '规则类型',
  field_name: '字段名',
  operator: '运算符',
  threshold_value: '阈值',
  logic_op: '逻辑操作',
  weight: '权重',
  priority: '优先级',
  action: '动作',
  is_active: '启用状态',
  description: '描述',
};

export function DiffView({ left, right, leftLabel = '版本 A', rightLabel = '版本 B', fields }: DiffViewProps) {
  const compareFields = fields || Object.keys({ ...left, ...right });

  return (
    <div className="border border-border rounded-card overflow-hidden">
      {/* 头部 */}
      <div className="grid grid-cols-2 divide-x divide-border bg-bg-tertiary/50">
        <div className="px-4 py-2.5 text-caption font-semibold text-text-primary">{leftLabel}</div>
        <div className="px-4 py-2.5 text-caption font-semibold text-text-primary">{rightLabel}</div>
      </div>

      {/* 对比行 */}
      <div className="divide-y divide-border/30">
        {compareFields.map((field) => {
          const leftVal = left[field];
          const rightVal = right[field];
          const isChanged = JSON.stringify(leftVal) !== JSON.stringify(rightVal);
          const label = FIELD_LABELS[field] || field;

          return (
            <div
              key={field}
              className={clsx(
                'grid grid-cols-2 divide-x divide-border/30',
                isChanged && 'bg-risk-low/5'
              )}
            >
              <div className={clsx('px-4 py-3', isChanged && 'bg-risk-low/8')}>
                <div className="flex items-center gap-2">
                  <span className="text-caption text-text-muted">{label}</span>
                  {isChanged && <span className="text-caption text-risk-low">已变更</span>}
                </div>
                <div className="text-body text-text-primary mt-1 font-mono text-sm">
                  {formatValue(leftVal)}
                </div>
              </div>
              <div className={clsx('px-4 py-3', isChanged && 'bg-risk-medium/8')}>
                <div className="flex items-center gap-2">
                  <span className="text-caption text-text-muted">{label}</span>
                </div>
                <div className={clsx(
                  'text-body mt-1 font-mono text-sm',
                  isChanged ? 'text-text-primary font-semibold' : 'text-text-primary'
                )}>
                  {formatValue(rightVal)}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}