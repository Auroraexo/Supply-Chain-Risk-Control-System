import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import { analysisService } from '@/services/analysisService';
import type { AnalysisResult } from '@/types/models';

export function AnalysisDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAnalysis() {
      if (!id) return;
      try {
        const res = await analysisService.getById(id);
        setAnalysis(res.data);
      } catch (error) {
        console.error('Failed to fetch analysis:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchAnalysis();
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-20" />
          <div>
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-48 mt-2" />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} glass>
              <Skeleton className="h-4 w-20 mb-2" />
              <Skeleton className="h-8 w-16" />
            </Card>
          ))}
        </div>
        <Card>
          <Skeleton className="h-6 w-32 mb-4" />
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </div>
        </Card>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
          返回
        </Button>
        <Card className="p-12 text-center">
          <p className="text-body text-text-muted">分析结果不存在</p>
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
          <h1 className="text-h1 text-text-primary">分析详情</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-body text-text-secondary">{analysis.request_id}</span>
            <RiskLevelBadge level={analysis.risk_level} />
          </div>
        </div>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card glass>
          <p className="text-caption text-text-muted">风险评分</p>
          <p className="text-h1 font-mono text-risk-high mt-1">{(analysis.risk_score * 100).toFixed(0)}</p>
          <p className="text-caption text-text-muted mt-1">/100分</p>
        </Card>
        <Card glass>
          <p className="text-caption text-text-muted">风险等级</p>
          <p className="text-h1 mt-1"><RiskLevelBadge level={analysis.risk_level} /></p>
        </Card>
        <Card glass>
          <p className="text-caption text-text-muted">异常标签</p>
          <p className="text-h3 text-text-primary mt-1 font-mono">{analysis.anomaly_tags?.length || 0}</p>
        </Card>
      </div>

      {/* Anomaly Tags */}
      <Card>
        <h3 className="text-h3 text-text-primary mb-4">异常标签</h3>
        <div className="flex flex-wrap gap-2">
          {analysis.anomaly_tags?.map((tag, i) => (
            <Badge key={i} variant="high">{tag}</Badge>
          )) || <span className="text-text-muted">无</span>}
        </div>
      </Card>

      {/* Analysis Reasoning */}
      <Card>
        <h3 className="text-h3 text-text-primary mb-4">分析推理</h3>
        <p className="text-body text-text-secondary leading-relaxed whitespace-pre-wrap">
          {analysis.reasoning || '暂无分析推理'}
        </p>
      </Card>

      {/* Facts Summary */}
      {analysis.facts_summary && (
        <Card>
          <h3 className="text-h3 text-text-primary mb-4">关键事实摘要</h3>
          <pre className="bg-bg-primary rounded-input p-4 text-caption text-text-primary font-mono overflow-x-auto">
            {JSON.stringify(analysis.facts_summary, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  );
}