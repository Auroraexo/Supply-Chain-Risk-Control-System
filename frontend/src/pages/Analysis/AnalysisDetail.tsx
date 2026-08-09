import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import type { AnalysisResult } from '@/types/models';

const mockDetail: AnalysisResult = {
  id: '1',
  request_id: 'REQ-001',
  raw_data_id: '1',
  risk_level: 'high',
  risk_score: 0.82,
  anomaly_tags: ['供应商延迟风险', '库存水平偏低', '物流时效波动'],
  reasoning: '供应商A历史交货延迟率超过30%，近3个月平均延迟5天；SKU-12345当前库存为安全库存的60%；华东区域物流时效标准差增加2天。综合风险评分0.82，属于高风险等级。',
  facts_summary: {
    supplier: '供应商A',
    delay_rate: 0.30,
    avg_delay_days: 5,
    inventory_ratio: 0.60,
    logistics_std_dev: 2,
  },
  created_at: '2026-08-07T10:35:00Z',
  updated_at: '2026-08-07T10:36:00Z',
};

export function AnalysisDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
          返回
        </Button>
        <div>
          <h1 className="text-h1 text-text-primary">分析详情</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-body text-text-secondary">{mockDetail.request_id}</span>
            <RiskLevelBadge level={mockDetail.risk_level} />
          </div>
        </div>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card glass>
          <p className="text-caption text-text-muted">风险评分</p>
          <p className="text-h1 font-mono text-risk-high mt-1">{(mockDetail.risk_score * 100).toFixed(0)}</p>
          <p className="text-caption text-text-muted mt-1">/100分</p>
        </Card>
        <Card glass>
          <p className="text-caption text-text-muted">风险等级</p>
          <p className="text-h1 mt-1"><RiskLevelBadge level={mockDetail.risk_level} /></p>
        </Card>
        <Card glass>
          <p className="text-caption text-text-muted">异常标签</p>
          <p className="text-h3 text-text-primary mt-1 font-mono">{mockDetail.anomaly_tags?.length || 0}</p>
        </Card>
      </div>

      {/* Anomaly Tags */}
      <Card>
        <h3 className="text-h3 text-text-primary mb-4">异常标签</h3>
        <div className="flex flex-wrap gap-2">
          {mockDetail.anomaly_tags?.map((tag, i) => (
            <Badge key={i} variant="high">{tag}</Badge>
          )) || <span className="text-text-muted">无</span>}
        </div>
      </Card>

      {/* Analysis Reasoning */}
      <Card>
        <h3 className="text-h3 text-text-primary mb-4">分析推理</h3>
        <p className="text-body text-text-secondary leading-relaxed whitespace-pre-wrap">
          {mockDetail.reasoning || '暂无分析推理'}
        </p>
      </Card>

      {/* Facts Summary */}
      {mockDetail.facts_summary && (
        <Card>
          <h3 className="text-h3 text-text-primary mb-4">关键事实摘要</h3>
          <pre className="bg-bg-primary rounded-input p-4 text-caption text-text-primary font-mono overflow-x-auto">
            {JSON.stringify(mockDetail.facts_summary, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  );
}