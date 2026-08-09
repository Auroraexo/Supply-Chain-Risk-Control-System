import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Search } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import { useToastStore } from '@/stores/toastStore';
import type { AnalysisResult } from '@/types/models';

const mockAnalyses: AnalysisResult[] = [
  { id: '1', request_id: 'REQ-001', raw_data_id: '1', risk_level: 'high', risk_score: 0.82, anomaly_tags: ['供应商延迟'], reasoning: '供应商A历史交货延迟率超过30%', facts_summary: null, created_at: '2026-08-07T10:35:00Z', updated_at: '2026-08-07T10:36:00Z' },
  { id: '2', request_id: 'REQ-002', raw_data_id: '2', risk_level: 'medium', risk_score: 0.55, anomaly_tags: ['价格波动'], reasoning: '原材料价格波动在可接受范围内', facts_summary: null, created_at: '2026-08-07T09:20:00Z', updated_at: null },
  { id: '3', request_id: 'REQ-003', raw_data_id: '3', risk_level: 'low', risk_score: 0.15, anomaly_tags: ['物流正常'], reasoning: '物流时效在正常范围内', facts_summary: null, created_at: '2026-08-07T08:05:00Z', updated_at: '2026-08-07T08:06:00Z' },
  { id: '4', request_id: 'REQ-005', raw_data_id: '5', risk_level: 'critical', risk_score: 0.95, anomaly_tags: ['库存严重不足'], reasoning: '关键物料库存低于安全线50%', facts_summary: null, created_at: '2026-08-06T14:25:00Z', updated_at: '2026-08-06T14:26:00Z' },
];

export function AnalysisList() {
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const { addToast } = useToastStore();
  const navigate = useNavigate();

  const filtered = mockAnalyses.filter((a) => {
    if (search && !a.request_id.toLowerCase().includes(search.toLowerCase())) return false;
    if (riskFilter && a.risk_level !== riskFilter) return false;
    return true;
  });

  const handleRunAnalysis = () => {
    addToast({ type: 'info', title: '分析任务已提交', message: '正在排队处理中...' });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-text-primary">风险分析中心</h1>
          <p className="text-body text-text-secondary mt-1">查看所有风险评估结果与分析详情</p>
        </div>
        <Button onClick={handleRunAnalysis}>
          <Play size={16} />
          新建分析
        </Button>
      </div>

      <Card padding="none">
        <div className="flex items-center gap-3 p-4 border-b border-border">
          <Input
            placeholder="搜索请求ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select
            options={[
              { value: '', label: '全部等级' },
              { value: 'critical', label: '严重' },
              { value: 'high', label: '高风险' },
              { value: 'medium', label: '中风险' },
              { value: 'low', label: '低风险' },
            ]}
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="w-28"
          />
        </div>

        <div className="divide-y divide-border/30">
          {filtered.map((analysis) => (
            <div
              key={analysis.id}
              className="flex items-center gap-4 p-4 hover:bg-bg-tertiary/20 cursor-pointer transition-colors"
              onClick={() => navigate(`/analysis/${analysis.id}`)}
            >
              <div className="flex-shrink-0">
                <RiskLevelBadge level={analysis.risk_level} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-body font-medium text-text-primary">{analysis.request_id}</span>
                  <Badge variant={analysis.updated_at ? 'success' : 'info'} dot={!analysis.updated_at}>
                    {analysis.updated_at ? '已完成' : '分析中'}
                  </Badge>
                </div>
                <p className="text-caption text-text-secondary mt-1 line-clamp-1">
                  {analysis.anomaly_tags?.join('、') || analysis.reasoning?.slice(0, 60) || '暂无描述'}
                </p>
              </div>
              <div className="hidden sm:block w-32">
                <ProgressBar value={analysis.risk_score * 100} size="sm" variant={
                  analysis.risk_level === 'critical' ? 'red' : analysis.risk_level === 'high' ? 'amber' : 'green'
                } showLabel />
                <p className="text-caption text-text-muted mt-1 text-center">风险评分</p>
              </div>
              <div className="hidden md:block text-right">
                <p className="text-caption text-text-muted">
                  {new Date(analysis.created_at).toLocaleDateString('zh-CN')}
                </p>
                <p className="text-caption text-text-muted">
                  {new Date(analysis.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}