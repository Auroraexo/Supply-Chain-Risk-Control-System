import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, CheckCircle, Clock3, FileCheck2, ShieldAlert, XCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatePanel } from '@/components/ui/StatePanel';
import { useToastStore } from '@/stores/toastStore';
import { decisionService } from '@/services/decisionService';
import type { DecisionResult } from '@/types/models';
import { AuditPanel } from '@/components/business/AuditPanel';
import { TreatmentPanel } from '@/components/business/TreatmentPanel';
import { useAuthStore } from '@/stores/authStore';

type ReviewAction = 'approve' | 'reject' | 'escalate';

export function DecisionApproval() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToastStore();
  const [decision, setDecision] = useState<DecisionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [submitting, setSubmitting] = useState<ReviewAction | null>(null);
  const [comment, setComment] = useState('');
  const user = useAuthStore(s => s.user);

  const fetchDecision = useCallback(async () => {
    if (!id) return;
    setLoading(true); setLoadError(false);
    try { const res = await decisionService.getById(id); setDecision(res.data); }
    catch { setLoadError(true); setDecision(null); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { void fetchDecision(); }, [fetchDecision]);

  const submit = async (action: ReviewAction) => {
    if (!id) return;
    if ((action === 'reject' || action === 'escalate') && !comment.trim()) {
      addToast({ type: 'error', title: '请填写审批意见', message: action === 'reject' ? '驳回必须说明原因' : '升级处理必须说明需要协同的事项' }); return;
    }
    setSubmitting(action);
    try {
      if (action === 'approve') await decisionService.approve(id, comment.trim() || '审批通过');
      if (action === 'reject') await decisionService.reject(id, comment.trim());
      if (action === 'escalate') await decisionService.escalate(id, comment.trim());
      addToast({ type: 'success', title: action === 'approve' ? '已批准' : action === 'reject' ? '已驳回' : '已升级处理', message: '审批记录已写入审计链路' });
      navigate('/decisions');
    } catch { addToast({ type: 'error', title: '提交失败', message: '审批操作未完成，请重试' }); }
    finally { setSubmitting(null); }
  };

  if (loading) return <div className="space-y-5"><Skeleton className="h-20 w-full"/><div className="grid gap-4 lg:grid-cols-3"><Skeleton className="h-[460px] lg:col-span-2"/><Skeleton className="h-[460px]"/></div></div>;
  if (loadError) return <StatePanel title="无法加载审批任务" description="决策数据当前不可用，请检查服务状态后重试。" onRetry={fetchDecision}/>;
  if (!decision) return <StatePanel title="审批任务不存在" description="该任务可能已被删除或请求地址无效。"/>;

  const confidence = Math.round((decision.confidence || 0) * 100);
  const isPending = (decision.decision === 'pending_review' || decision.decision === 'escalate') && (user?.role === 'decider' || user?.role === 'admin');
  return (
    <div className="space-y-5 animate-fade-in pb-28 lg:pb-0">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3"><Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="mt-1"><ArrowLeft size={16}/>返回</Button><div><div className="flex flex-wrap items-center gap-2"><h1 className="text-h1 text-text-primary">决策研判与审批</h1><Badge variant={isPending ? 'info' : decision.decision === 'approve' ? 'success' : 'high'} dot={isPending}>{isPending ? '待人工审批' : decision.decision}</Badge></div><p className="mt-1 font-mono text-caption text-text-secondary">{decision.request_id}</p></div></div>
        <div className="flex items-center gap-2 text-caption text-text-muted"><Clock3 size={14}/>{new Date(decision.created_at).toLocaleString('zh-CN')}</div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <TreatmentPanel key={`${decision.id}-${decision.revision}`} decision={decision} onSaved={fetchDecision}/>
          <AuditPanel key={`audit-${decision.revision}`} decisionId={decision.id}/>
          <Card padding="lg">
            <div className="mb-5 flex items-center justify-between"><div><p className="text-caption font-semibold text-accent-blue">系统建议</p><h2 className="mt-1 text-h2 text-text-primary">{decision.decision === 'approve' ? '建议通过并持续监控' : decision.decision === 'reject' ? '建议阻断当前操作' : '建议转人工研判'}</h2></div><div className="text-right"><p className="font-mono text-[30px] font-bold text-text-primary">{confidence}%</p><p className="text-[11px] text-text-muted">模型置信度</p></div></div>
            <div className="h-2 overflow-hidden rounded-full bg-bg-tertiary"><div className={`h-full rounded-full ${confidence >= 80 ? 'bg-risk-low' : confidence >= 60 ? 'bg-risk-medium' : 'bg-risk-critical'}`} style={{width:`${confidence}%`}}/></div>
            <p className="mt-5 whitespace-pre-wrap text-body leading-7 text-text-secondary">{decision.explanation || '当前决策没有提供解释。建议在审批前返回风险分析页面核对证据。'}</p>
          </Card>

          <Card padding="lg">
            <div className="mb-4 flex items-center gap-2"><FileCheck2 size={18} className="text-accent-blue"/><h2 className="text-h3 text-text-primary">决策依据与审计信息</h2></div>
            <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
              {[['请求 ID',decision.request_id],['分析记录',decision.analysis_id],['反思校验',decision.reflection_passed == null ? '未执行' : decision.reflection_passed ? '已通过' : '未通过'],['当前审核人',decision.reviewed_by || '尚未分配'],['创建时间',new Date(decision.created_at).toLocaleString('zh-CN')],['最近更新',decision.updated_at ? new Date(decision.updated_at).toLocaleString('zh-CN') : '暂无']].map(([label,value]) => <div key={label} className="border-b border-border/70 pb-3"><dt className="text-caption text-text-muted">{label}</dt><dd className="mt-1 break-all text-body font-medium text-text-primary">{value}</dd></div>)}
            </dl>
            {decision.decision_path?.length ? <div className="mt-5"><p className="mb-3 text-caption font-semibold text-text-secondary">决策路径</p><div className="flex flex-wrap items-center gap-2">{decision.decision_path.map((step,index)=><span key={`${step}-${index}`} className="flex items-center gap-2"><Badge variant="default">{step}</Badge>{index < decision.decision_path!.length-1 && <span className="text-text-muted">→</span>}</span>)}</div></div> : null}
          </Card>
        </div>

        <aside className="space-y-4">
          <Card padding="lg" className="lg:sticky lg:top-24">
            <div className="mb-4 flex items-center gap-2"><ShieldAlert size={19} className="text-risk-medium"/><h2 className="text-h3 text-text-primary">审批操作</h2></div>
            {!isPending ? <div className="rounded-btn bg-bg-tertiary/60 p-4 text-caption text-text-secondary">该决策已完成处理。审批操作已锁定，以保护审计记录。</div> : <>
              <label className="text-caption font-semibold text-text-secondary" htmlFor="review-comment">审批意见</label>
              <textarea id="review-comment" rows={6} value={comment} onChange={e=>setComment(e.target.value)} placeholder="记录判断依据、补充条件或协同事项……" className="mt-2 w-full resize-none rounded-input border border-border bg-bg-primary p-3 text-body text-text-primary outline-none placeholder:text-text-muted focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"/>
              <p className="mt-1 text-[11px] text-text-muted">驳回和升级处理必须填写意见，所有操作会进入审计日志。</p>
              <div className="mt-5 space-y-2.5"><Button className="w-full" size="lg" onClick={()=>submit('approve')} loading={submitting==='approve'} disabled={Boolean(submitting)}><CheckCircle size={18}/>批准建议</Button><Button className="w-full" variant="danger" onClick={()=>submit('reject')} loading={submitting==='reject'} disabled={Boolean(submitting)}><XCircle size={18}/>驳回建议</Button><Button className="w-full" variant="outline" onClick={()=>submit('escalate')} loading={submitting==='escalate'} disabled={Boolean(submitting)}><AlertTriangle size={18}/>升级处理</Button></div>
            </>}
          </Card>
        </aside>
      </section>

      {isPending && <div className="fixed inset-x-0 bottom-0 z-20 flex gap-2 border-t border-border bg-bg-secondary/95 p-3 backdrop-blur lg:hidden"><Button variant="danger" className="flex-1" onClick={()=>submit('reject')} disabled={Boolean(submitting)}>驳回</Button><Button variant="outline" className="flex-1" onClick={()=>submit('escalate')} disabled={Boolean(submitting)}>升级</Button><Button className="flex-1" onClick={()=>submit('approve')} disabled={Boolean(submitting)}>批准</Button></div>}
    </div>
  );
}
