import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Search } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import { Skeleton } from '@/components/ui/Skeleton';
import { useToastStore } from '@/stores/toastStore';
import { analysisService } from '@/services/analysisService';
import type { AnalysisResult } from '@/types/models';

export function AnalysisList() {
  const [analyses, setAnalyses] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const { addToast } = useToastStore();
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await analysisService.list({ page: 1, page_size: 50 });
      setAnalyses(res.data.items);
    } catch (error) {
      console.error('Failed to fetch analyses:', error);
      addToast({ type: 'error', title: '加载失败', message: '无法获取分析结果' });
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = analyses.filter((a) => {
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

        {loading ? (
          <div className="p-8 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-text-muted">
            <Search size={32} className="mx-auto mb-3 opacity-40" />
            <p className="text-body">暂无分析结果</p>
            <p className="text-caption mt-1">点击"新建分析"创建第一个分析任务</p>
          </div>
        ) : (
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
        )}
      </Card>
    </div>
  );
}