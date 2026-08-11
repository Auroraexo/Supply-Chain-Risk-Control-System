import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { useToastStore } from '@/stores/toastStore';
import { decisionService } from '@/services/decisionService';
import type { DecisionResult } from '@/types/models';

export function DecisionApproval() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToastStore();
  const [decision, setDecision] = useState<DecisionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    async function fetchDecision() {
      if (!id) return;
      try {
        const res = await decisionService.getById(id);
        setDecision(res.data);
      } catch (error) {
        console.error('Failed to fetch decision:', error);
        addToast({ type: 'error', title: '加载失败', message: '无法获取决策详情' });
      } finally {
        setLoading(false);
      }
    }
    fetchDecision();
  }, [id, addToast]);

  const handleApprove = async () => {
    if (!id) return;
    setApproving(true);
    try {
      await decisionService.approve(id, '审批通过');
      addToast({ type: 'success', title: '审批通过', message: '决策已批准' });
      navigate('/decisions');
    } catch (error) {
      addToast({ type: 'error', title: '审批失败', message: '决策审批失败' });
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    if (!id) return;
    setApproving(true);
    try {
      await decisionService.reject(id, '审批驳回');
      addToast({ type: 'error', title: '审批驳回', message: '决策已驳回' });
      navigate('/decisions');
    } catch (error) {
      addToast({ type: 'error', title: '操作失败', message: '决策驳回失败' });
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-20" />
          <div>
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-24 mt-2" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <Card>
              <Skeleton className="h-6 w-32 mb-4" />
              <div className="space-y-3">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <Skeleton key={i} className="h-4 w-full" />
                ))}
              </div>
            </Card>
          </div>
          <Card>
            <Skeleton className="h-6 w-24 mb-4" />
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          </Card>
        </div>
      </div>
    );
  }

  if (!decision) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
          返回
        </Button>
        <Card className="p-12 text-center">
          <p className="text-body text-text-muted">决策不存在</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
          返回
        </Button>
        <div>
          <h1 className="text-h1 text-text-primary">决策审批</h1>
          <p className="text-body text-text-secondary mt-1">{decision.request_id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <h3 className="text-h3 text-text-primary mb-4">决策详情</h3>
            <dl className="space-y-3">
              {[
                { label: '请求ID', value: decision.request_id },
                { label: '决策类型', value: decision.decision },
                { label: '风险评分', value: decision.confidence ? `${(decision.confidence * 100).toFixed(0)}%` : '-' },
                { label: '置信度', value: decision.confidence ? `${(decision.confidence * 100).toFixed(0)}%` : '-' },
                { label: '审核人', value: decision.reviewed_by || '未审核' },
                { label: '创建时间', value: new Date(decision.created_at).toLocaleString('zh-CN') },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between">
                  <dt className="text-body text-text-muted">{label}</dt>
                  <dd className="text-body text-text-primary font-medium">{value}</dd>
                </div>
              ))}
            </dl>
          </Card>

          {decision.explanation && (
            <Card>
              <h3 className="text-h3 text-text-primary mb-4">决策说明</h3>
              <p className="text-body text-text-secondary">{decision.explanation}</p>
            </Card>
          )}
        </div>

        <Card className="h-fit">
          <h3 className="text-h3 text-text-primary mb-4">审批操作</h3>
          <div className="space-y-3">
            <Button className="w-full" size="lg" onClick={handleApprove} loading={approving}>
              <CheckCircle size={18} />
              批准
            </Button>
            <Button className="w-full" variant="danger" size="lg" onClick={handleReject} loading={approving}>
              <XCircle size={18} />
              驳回
            </Button>
            <Button className="w-full" variant="outline" size="lg">
              <AlertTriangle size={18} />
              升级处理
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}