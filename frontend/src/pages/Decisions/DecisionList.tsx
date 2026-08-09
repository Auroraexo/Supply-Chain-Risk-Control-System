import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import type { DecisionResult, DecisionStatus } from '@/types/models';

const mockDecisions: DecisionResult[] = [
  { id: '1', request_id: 'REQ-001', analysis_id: '1', decision: 'pending_review', confidence: 0.82, explanation: '高风险项需要人工审核', decision_path: null, reflection_passed: null, reviewed_by: null, created_at: '2026-08-07T10:36:00Z', updated_at: null },
  { id: '2', request_id: 'REQ-003', analysis_id: '3', decision: 'approve', confidence: 0.95, explanation: '低风险自动通过', decision_path: ['rule-1'], reflection_passed: true, reviewed_by: null, created_at: '2026-08-07T08:06:00Z', updated_at: '2026-08-07T08:06:05Z' },
  { id: '3', request_id: 'REQ-005', analysis_id: '4', decision: 'reject', confidence: 0.88, explanation: '严重风险自动拒绝', decision_path: ['rule-2'], reflection_passed: true, reviewed_by: null, created_at: '2026-08-06T14:26:00Z', updated_at: '2026-08-06T14:26:10Z' },
  { id: '4', request_id: 'REQ-006', analysis_id: '5', decision: 'escalate', confidence: 0.60, explanation: '需要升级处理', decision_path: null, reflection_passed: false, reviewed_by: 'user-1', created_at: '2026-08-06T12:00:00Z', updated_at: '2026-08-06T15:00:00Z' },
];

const statusConfig: Record<string, { label: string; variant: 'info' | 'success' | 'high' | 'default' }> = {
  pending_review: { label: '待审批', variant: 'info' },
  approve: { label: '已通过', variant: 'success' },
  reject: { label: '已驳回', variant: 'high' },
  escalate: { label: '已升级', variant: 'default' },
};

const typeLabels: Record<string, string> = {
  approve: '自动通过',
  reject: '自动拒绝',
  pending_review: '人工审核',
  escalate: '已升级',
};

export function DecisionList() {
  const [statusFilter, setStatusFilter] = useState('');
  const navigate = useNavigate();

  const filtered = mockDecisions.filter((d) => {
    if (statusFilter && d.decision !== statusFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-h1 text-text-primary">决策管理</h1>
        <p className="text-body text-text-secondary mt-1">管理风险决策审批与执行</p>
      </div>

      <Card padding="none">
        <div className="flex items-center gap-3 p-4 border-b border-border">
          <Select
            options={[
              { value: '', label: '全部状态' },
              { value: 'pending_review', label: '待审批' },
              { value: 'approve', label: '已通过' },
              { value: 'reject', label: '已驳回' },
              { value: 'escalate', label: '已升级' },
            ]}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-28"
          />
        </div>

        <div className="divide-y divide-border/30">
          {filtered.map((decision) => {
            const cfg = statusConfig[decision.decision] || { label: decision.decision, variant: 'default' as const };
            return (
              <div
                key={decision.id}
                className="flex items-center gap-4 p-4 hover:bg-bg-tertiary/20 cursor-pointer transition-colors"
                onClick={() => navigate(`/decisions/${decision.id}`)}
              >
                <Badge variant={cfg.variant} dot={decision.decision === 'pending_review'}>
                  {cfg.label}
                </Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-body font-medium text-text-primary">{decision.request_id}</p>
                  <p className="text-caption text-text-secondary mt-1 line-clamp-1">{decision.explanation}</p>
                </div>
                <div className="hidden sm:block">
                  <Badge variant="default">{typeLabels[decision.decision]}</Badge>
                </div>
                <div className="hidden md:block text-right">
                  <p className="text-caption text-text-muted">
                    {new Date(decision.created_at).toLocaleDateString('zh-CN')}
                  </p>
                  <p className="text-caption text-text-muted">
                    {new Date(decision.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}