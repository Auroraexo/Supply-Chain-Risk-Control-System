import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle, Clock, FileSearch, GitBranch, Loader2, Scale, ShieldAlert, XCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatePanel } from '@/components/ui/StatePanel';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import { analysisService } from '@/services/analysisService';
import { agentLogService } from '@/services/agentLogService';
import type { AgentExecutionStep, AnalysisResult, DecisionTrace } from '@/types/models';

export function AnalysisDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [trace, setTrace] = useState<DecisionTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [traceLoading, setTraceLoading] = useState(false);

  const fetchAnalysis = useCallback(async () => {
    if (!id) return;
    setLoading(true); setLoadError(false);
    try {
      const res = await analysisService.getById(id); setAnalysis(res.data);
      if (res.data?.request_id) { setTraceLoading(true); try { const t = await agentLogService.getDecisionTrace(res.data.request_id); setTrace(t.data); } catch { setTrace(null); } finally { setTraceLoading(false); } }
    } catch { setLoadError(true); setAnalysis(null); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { void fetchAnalysis(); }, [fetchAnalysis]);
  if (loading) return <div className="space-y-5"><Skeleton className="h-20"/><div className="grid gap-4 lg:grid-cols-3"><Skeleton className="h-[500px] lg:col-span-2"/><Skeleton className="h-[500px]"/></div></div>;
  if (loadError) return <StatePanel title="无法加载风险分析" description="分析数据暂时不可用，请稍后重试。" onRetry={fetchAnalysis}/>;
  if (!analysis) return <StatePanel title="分析结果不存在" description="该结果可能已删除或请求地址无效。"/>;

  const score = Math.round(analysis.risk_score * 100);
  const facts = analysis.facts_summary ? Object.entries(analysis.facts_summary) : [];
  const riskTone = analysis.risk_level === 'critical' ? 'text-risk-critical' : analysis.risk_level === 'high' ? 'text-risk-high' : analysis.risk_level === 'medium' ? 'text-risk-medium' : 'text-risk-low';
  return (
    <div className="space-y-5 animate-fade-in">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3"><Button variant="ghost" size="sm" onClick={()=>navigate(-1)} className="mt-1"><ArrowLeft size={16}/>返回</Button><div><div className="flex flex-wrap items-center gap-2"><h1 className="text-h1 text-text-primary">风险事件研判</h1><RiskLevelBadge level={analysis.risk_level}/></div><p className="mt-1 font-mono text-caption text-text-secondary">{analysis.request_id}</p></div></div>
        <Button onClick={()=>navigate('/decisions')}><Scale size={16}/>进入决策队列</Button>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card padding="lg" className="overflow-hidden">
            <div className="grid gap-6 sm:grid-cols-[180px_1fr] sm:items-center">
              <div className="relative mx-auto flex h-40 w-40 items-center justify-center rounded-full" style={{background:`conic-gradient(var(--color-risk-${analysis.risk_level === 'none' ? 'low' : analysis.risk_level}) ${score * 3.6}deg, var(--color-bg-tertiary) 0)`}}><div className="flex h-32 w-32 flex-col items-center justify-center rounded-full bg-bg-secondary"><span className={`font-mono text-[42px] font-bold leading-none ${riskTone}`}>{score}</span><span className="mt-1 text-caption text-text-muted">风险评分 / 100</span></div></div>
              <div><p className="text-caption font-semibold text-accent-blue">AI 风险研判结论</p><h2 className="mt-2 text-h2 text-text-primary">{analysis.risk_level === 'critical' ? '发现重大供应链风险，建议立即处置' : analysis.risk_level === 'high' ? '发现高风险信号，需要优先人工复核' : analysis.risk_level === 'medium' ? '存在潜在风险，建议持续观察' : '当前风险处于可控范围'}</h2><p className="mt-3 whitespace-pre-wrap text-body leading-7 text-text-secondary">{analysis.reasoning || '系统尚未生成详细推理。请结合下方事实证据完成研判。'}</p></div>
            </div>
          </Card>

          <Card padding="lg">
            <div className="mb-4 flex items-center gap-2"><FileSearch size={19} className="text-accent-blue"/><h2 className="text-h3 text-text-primary">事实证据</h2><Badge variant="default">{facts.length} 项</Badge></div>
            {facts.length ? <div className="grid gap-3 sm:grid-cols-2">{facts.map(([key,value])=><div key={key} className="rounded-btn border border-border bg-bg-primary p-4"><p className="text-caption font-semibold text-text-secondary">{key}</p><p className="mt-2 break-words text-body text-text-primary">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</p></div>)}</div> : <p className="rounded-btn bg-bg-tertiary/40 p-4 text-caption text-text-muted">暂无结构化事实证据，请核对原始数据后再做高风险决策。</p>}
          </Card>

          <Card padding="lg">
            <div className="mb-4 flex items-center gap-2"><GitBranch size={19} className="text-accent-purple"/><h2 className="text-h3 text-text-primary">Agent 决策链路</h2></div>
            {traceLoading ? <div className="flex items-center gap-2 py-8 text-text-muted"><Loader2 size={16} className="animate-spin"/>正在加载决策追踪...</div> : trace ? <div>{trace.steps.map((step,index)=><StepTimeline key={`${step.step}-${index}`} step={step} isLast={index===trace.steps.length-1}/>)}<div className="mt-2 flex flex-wrap items-center gap-2 border-t border-border pt-4"><span className="text-caption text-text-muted">最终建议</span><Badge variant={trace.final_decision === 'approve' ? 'success' : 'high'}>{trace.final_decision}</Badge><span className="text-caption text-text-muted">置信度 {Math.round(trace.confidence*100)}%</span></div></div> : <p className="rounded-btn bg-bg-tertiary/40 p-4 text-caption text-text-muted">暂无 Agent 执行链路，当前分析可能尚未进入决策阶段。</p>}
          </Card>
        </div>

        <aside className="space-y-4">
          <Card padding="lg"><div className="flex items-center gap-2"><ShieldAlert size={19} className={riskTone}/><h2 className="text-h3 text-text-primary">风险摘要</h2></div><dl className="mt-5 space-y-4">{[['风险等级',<RiskLevelBadge key="risk" level={analysis.risk_level} size="sm"/>],['风险评分',`${score} / 100`],['异常标签',`${analysis.anomaly_tags?.length || 0} 个`],['原始数据',analysis.raw_data_id],['分析时间',new Date(analysis.created_at).toLocaleString('zh-CN')]].map(([label,value])=><div key={String(label)} className="flex items-start justify-between gap-4 border-b border-border/70 pb-3"><dt className="text-caption text-text-muted">{label}</dt><dd className="max-w-[65%] break-all text-right text-caption font-semibold text-text-primary">{value}</dd></div>)}</dl></Card>
          <Card padding="lg"><h2 className="text-h3 text-text-primary">异常信号</h2><div className="mt-4 flex flex-wrap gap-2">{analysis.anomaly_tags?.length ? analysis.anomaly_tags.map(tag=><Badge key={tag} variant="high">{tag}</Badge>) : <span className="text-caption text-text-muted">未发现异常标签</span>}</div></Card>
        </aside>
      </section>
    </div>
  );
}

function StepTimeline({ step, isLast }: { step: AgentExecutionStep; isLast: boolean }) {
  const icon = step.status === 'success' ? <CheckCircle size={16} className="text-risk-low"/> : step.status === 'error' ? <XCircle size={16} className="text-risk-critical"/> : <Clock size={16} className="text-risk-medium"/>;
  return <div className="flex gap-3"><div className="flex flex-col items-center"><div className="flex h-7 w-7 items-center justify-center rounded-full border border-border bg-bg-primary">{icon}</div>{!isLast && <div className="my-1 w-px flex-1 bg-border"/>}</div><div className="min-w-0 flex-1 pb-5"><div className="flex flex-wrap items-center gap-2"><p className="text-body font-semibold text-text-primary">{step.action}</p><Badge variant="default">{step.step}</Badge><span className="ml-auto text-[11px] text-text-muted">{step.elapsed_ms}ms</span></div>{step.output && <p className="mt-1 line-clamp-2 text-caption text-text-secondary">{step.output}</p>}</div></div>;
}
