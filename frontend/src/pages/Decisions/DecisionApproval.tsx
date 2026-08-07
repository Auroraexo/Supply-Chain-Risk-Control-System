import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useToastStore } from '@/stores/toastStore';

export function DecisionApproval() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToastStore();
  const [approving, setApproving] = useState(false);

  const handleApprove = () => {
    setApproving(true);
    setTimeout(() => {
      setApproving(false);
      addToast({ type: 'success', title: '审批通过', message: '决策已批准' });
      navigate('/decisions');
    }, 800);
  };

  const handleReject = () => {
    setApproving(true);
    setTimeout(() => {
      setApproving(false);
      addToast({ type: 'error', title: '审批驳回', message: '决策已驳回' });
      navigate('/decisions');
    }, 800);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
          返回
        </Button>
        <div>
          <h1 className="text-h1 text-text-primary">决策审批</h1>
          <p className="text-body text-text-secondary mt-1">REQ-001</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <h3 className="text-h3 text-text-primary mb-4">决策详情</h3>
            <dl className="space-y-3">
              {[
                { label: '请求ID', value: 'REQ-001' },
                { label: '决策类型', value: '人工审核' },
                { label: '风险等级', value: '高风险' },
                { label: '风险评分', value: '82/100' },
                { label: '置信度', value: '91%' },
                { label: '创建时间', value: '2026-08-07 10:36:00' },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between">
                  <dt className="text-body text-text-muted">{label}</dt>
                  <dd className="text-body text-text-primary font-medium">{value}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card>
            <h3 className="text-h3 text-text-primary mb-4">审批理由</h3>
            <p className="text-body text-text-secondary">
              供应商A历史交货延迟率超过30%，近3个月平均延迟5天，属于高风险项。建议启动供应商替换流程，并加强库存缓冲。
            </p>
          </Card>
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