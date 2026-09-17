import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Search, LayoutGrid, List, Sparkles } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import { AutomationModal } from '@/components/business/AutomationModal';
import { NewAnalysisModal } from '@/components/business/NewAnalysisModal';
import { Skeleton } from '@/components/ui/Skeleton';
import { PageHeader } from '@/components/ui/PageHeader';
import Empty from '@/components/Empty';
import { useToastStore } from '@/stores/toastStore';
import { analysisService } from '@/services/analysisService';
import type { AnalysisResult } from '@/types/models';

export function AnalysisList() {
  const [analyses, setAnalyses] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(() => new URLSearchParams(window.location.search).get('q') || '');
  const [riskFilter, setRiskFilter] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'card'>('list');
  const [autoOpen, setAutoOpen] = useState(false);
  const [newOpen, setNewOpen] = useState(false);
  const { addToast } = useToastStore();
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await analysisService.list({ page: 1, page_size: 50 });
      setAnalyses(res?.items || []);
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
    setNewOpen(true);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader eyebrow="Risk Intelligence" title="风险分析中心" description="汇总风险事件、证据与智能研判结果" actions={<>
          <Button variant="outline" onClick={() => setAutoOpen(true)}>
            <Sparkles size={16} />
            AI 自动分析
          </Button>
          <Button onClick={handleRunAnalysis}>
            <Play size={16} />
            新建分析
          </Button>
        </>} />

      <AutomationModal mode="analysis" open={autoOpen} onClose={() => setAutoOpen(false)} onDone={fetchData} />
      <NewAnalysisModal open={newOpen} onClose={() => setNewOpen(false)} onDone={fetchData} />

      <Card padding="none">
        <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center">
          <Input
            placeholder="搜索请求ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full sm:max-w-xs"
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
          <div className="flex-1" />
          <div className="flex items-center border border-border rounded-input overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 transition-colors ${viewMode === 'list' ? 'bg-accent-blue text-white' : 'text-text-muted hover:text-text-primary'}`}
              title="列表视图"
              aria-label="列表视图"
              aria-pressed={viewMode === 'list'}
            >
              <List size={16} />
            </button>
            <button
              onClick={() => setViewMode('card')}
              className={`p-1.5 transition-colors ${viewMode === 'card' ? 'bg-accent-blue text-white' : 'text-text-muted hover:text-text-primary'}`}
              title="卡片视图"
              aria-label="卡片视图"
              aria-pressed={viewMode === 'card'}
            >
              <LayoutGrid size={16} />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-8 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <Empty title={search || riskFilter ? '未找到匹配的分析结果' : '暂无分析结果'} description={search || riskFilter ? '尝试调整搜索词或风险等级。' : '接入数据后启动第一个风险分析任务。'} icon={<Search size={24}/>} action={!search && !riskFilter ? <Button size="sm" onClick={handleRunAnalysis}><Play size={15}/>新建分析</Button> : undefined}/>
        ) : viewMode === 'card' ? (
          <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {filtered.map((analysis) => (
              <Card
                key={analysis.id}
                hover
                className="cursor-pointer"
                onClick={() => navigate(`/analysis/${analysis.id}`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <RiskLevelBadge level={analysis.risk_level} />
                  <Badge variant={analysis.updated_at ? 'success' : 'info'} dot={!analysis.updated_at}>
                    {analysis.updated_at ? '已完成' : '分析中'}
                  </Badge>
                </div>
                <p className="text-body font-medium text-text-primary mb-2 truncate">{analysis.request_id}</p>
                <div className="mb-3">
                  <ProgressBar
                    value={(analysis.risk_score ?? 0) * 100}
                    size="sm"
                    variant={analysis.risk_level === 'critical' ? 'red' : analysis.risk_level === 'high' ? 'amber' : 'green'}
                    showLabel
                  />
                </div>
                <div className="flex flex-wrap gap-1 mb-2">
                  {analysis.anomaly_tags?.slice(0, 4).map((tag, i) => (
                    <Badge key={i} variant="high">{tag}</Badge>
                  )) || <span className="text-caption text-text-muted">无异常标签</span>}
                </div>
                <p className="text-caption text-text-muted line-clamp-2">
                  {analysis.reasoning || '暂无分析推理'}
                </p>
                <div className="flex justify-between items-center mt-3 pt-3 border-t border-border/30">
                  <span className="text-caption text-text-muted">
                    {new Date(analysis.created_at).toLocaleDateString('zh-CN')}
                  </span>
                  <span className="text-caption text-text-muted font-mono">
                    评分: {((analysis.risk_score ?? 0) * 100).toFixed(0)}
                  </span>
                </div>
              </Card>
            ))}
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
                  <ProgressBar value={(analysis.risk_score ?? 0) * 100} size="sm" variant={
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
