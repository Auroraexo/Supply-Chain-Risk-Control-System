import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { Skeleton } from '@/components/ui/Skeleton';
import { Search } from 'lucide-react';
import { decisionService } from '@/services/decisionService';
import type { DecisionResult } from '@/types/models';

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
  const [decisions, setDecisions] = useState<DecisionResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await decisionService.list({ page: 1, page_size: 50 });
      setDecisions(res.data.items);
    } catch (error) {
      console.error('Failed to fetch decisions:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = decisions.filter((d) => {
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

        {loading ? (
          <div className="p-8 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-text-muted">
            <Search size={32} className="mx-auto mb-3 opacity-40" />
            <p className="text-body">暂无决策记录</p>
          </div>
        ) : (
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
        )}
      </Card>
    </div>
  );
}