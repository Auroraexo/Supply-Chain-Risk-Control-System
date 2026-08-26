import { useState, useCallback } from 'react';
import { Sparkles, CheckCircle2, XCircle, MinusCircle, Wand2 } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useToastStore } from '@/stores/toastStore';
import {
  automationService,
  type AutoAnalysisResult,
  type AutoReviewResult,
  type AutoRulesResult,
} from '@/services/automationService';

export type AutomationMode = 'analysis' | 'review' | 'rules';

const modeMeta: Record<AutomationMode, { title: string; desc: string; runLabel: string }> = {
  analysis: {
    title: 'AI 自动分析',
    desc: '自动捞取待处理原始数据，逐条运行 Agent 分析流水线（侦察→分析→反思→决策）',
    runLabel: '开始自动分析',
  },
  review: {
    title: 'AI 自动审核',
    desc: 'AI 审核员按置信度与风险等级自动终局待处理决策，低置信度决策保留人工审核',
    runLabel: '开始自动审核',
  },
  rules: {
    title: 'AI 规则优化',
    desc: 'AI 分析历史分析结果分布，生成规则优化建议，可选直接应用到规则树',
    runLabel: '生成优化建议',
  },
};

const actionVariant: Record<string, 'success' | 'critical' | 'default' | 'info'> = {
  approve: 'success',
  reject: 'critical',
  escalate: 'info',
  keep: 'default',
};

export function AutomationModal({
  mode,
  open,
  onClose,
  onDone,
}: {
  mode: AutomationMode;
  open: boolean;
  onClose: () => void;
  onDone?: () => void;
}) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [maxItems, setMaxItems] = useState(5);
  const [threshold, setThreshold] = useState(0.8);
  const [apply, setApply] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AutoAnalysisResult | null>(null);
  const [reviewResult, setReviewResult] = useState<AutoReviewResult | null>(null);
  const [rulesResult, setRulesResult] = useState<AutoRulesResult | null>(null);
  const { addToast } = useToastStore();

  const meta = modeMeta[mode];

  const handleClose = useCallback(() => {
    setRunning(false);
    setError('');
    setAnalysisResult(null);
    setReviewResult(null);
    setRulesResult(null);
    onClose();
  }, [onClose]);

  const handleRun = useCallback(async () => {
    setRunning(true);
    setError('');
    setAnalysisResult(null);
    setReviewResult(null);
    setRulesResult(null);
    try {
      if (mode === 'analysis') {
        const res = await automationService.runAnalysis(maxItems);
        setAnalysisResult(res.data);
        addToast({ type: 'success', title: '自动分析完成', message: `共 ${res.data.total} 条，成功 ${res.data.completed} 条` });
      } else if (mode === 'review') {
        const res = await automationService.runReview(threshold);
        setReviewResult(res.data);
        addToast({ type: 'success', title: '自动审核完成', message: `处理 ${res.data.processed} 条，保留人工 ${res.data.kept} 条` });
      } else {
        const res = await automationService.runRules(apply);
        setRulesResult(res.data);
        addToast({
          type: 'success',
          title: '规则优化完成',
          message: apply ? `已应用 ${res.data.applied.length} 条规则` : `生成 ${res.data.suggestions.length} 条建议`,
        });
      }
      onDone?.();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string | { message?: string } } } };
      let msg = '自动化执行失败，请稍后重试';
      if (axiosErr.response?.status === 403) {
        msg = '权限不足：规则优化需要管理员权限';
      } else if (axiosErr.response?.data?.detail) {
        const detail = axiosErr.response.data.detail;
        msg = typeof detail === 'string' ? detail : detail.message || msg;
      }
      setError(msg);
      addToast({ type: 'error', title: '执行失败', message: msg });
    } finally {
      setRunning(false);
    }
  }, [mode, maxItems, threshold, apply, addToast, onDone]);

  return (
    <Modal open={open} onClose={handleClose} title={meta.title} size="lg">
      <div className="space-y-4">
        {/* 说明 */}
        <div className="flex items-start gap-3 rounded-card border border-accent-blue/30 bg-accent-blue/10 p-3">
          <Sparkles size={18} className="text-accent-blue mt-0.5 flex-shrink-0" />
          <p className="text-caption text-text-secondary leading-relaxed">{meta.desc}</p>
        </div>

        {/* 参数配置 */}
        <div className="rounded-card border border-border bg-bg-primary p-4 space-y-3">
          {mode === 'analysis' && (
            <div className="flex items-center justify-between gap-4">
              <label className="text-caption font-medium text-text-secondary">单次最多分析条数</label>
              <input
                type="number"
                min={1}
                max={20}
                value={maxItems}
                onChange={(e) => setMaxItems(Math.max(1, Math.min(20, parseInt(e.target.value, 10) || 1)))}
                className="w-24 rounded-input border border-border bg-bg-secondary px-3 py-1.5 text-body text-text-primary outline-none focus:border-accent-blue"
              />
            </div>
          )}
          {mode === 'review' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-4">
                <label className="text-caption font-medium text-text-secondary">自动处理置信度阈值</label>
                <span className="text-body font-mono text-accent-blue">{threshold.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0.5}
                max={1}
                step={0.05}
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full accent-accent-blue"
              />
              <p className="text-caption text-text-muted">
                置信度 ≥ 阈值：低风险自动批准、高风险自动驳回；低于阈值保留人工审核
              </p>
            </div>
          )}
          {mode === 'rules' && (
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={apply}
                onChange={(e) => setApply(e.target.checked)}
                className="w-4 h-4 rounded accent-accent-blue"
              />
              <span className="text-caption font-medium text-text-secondary">
                将 AI 建议的规则直接应用到规则树（需要管理员权限）
              </span>
            </label>
          )}
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="flex items-center gap-2 rounded-card border border-risk-critical/30 bg-risk-critical/10 p-3">
            <XCircle size={16} className="text-risk-critical flex-shrink-0" />
            <p className="text-caption text-risk-critical">{error}</p>
          </div>
        )}

        {/* 执行结果 */}
        {analysisResult && (
          <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
            <div className="flex items-center gap-2">
              <Badge variant="info">共 {analysisResult.total} 条</Badge>
              <Badge variant="success">成功 {analysisResult.completed}</Badge>
              <Badge variant="critical">失败 {analysisResult.failed}</Badge>
            </div>
            {analysisResult.items.map((item) => (
              <div key={item.raw_data_id} className="flex items-center gap-3 rounded-card border border-border bg-bg-primary p-3">
                {item.status === 'completed' ? (
                  <CheckCircle2 size={16} className="text-risk-low flex-shrink-0" />
                ) : (
                  <XCircle size={16} className="text-risk-critical flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-caption text-text-primary font-mono truncate">{item.source_id}</p>
                  {item.error && <p className="text-caption text-risk-critical mt-0.5">{item.error}</p>}
                </div>
                {item.risk_level && <Badge variant={item.risk_level as 'low'}>{item.risk_level}</Badge>}
                {item.decision && <Badge variant={actionVariant[item.decision] || 'default'}>{item.decision}</Badge>}
              </div>
            ))}
          </div>
        )}

        {reviewResult && (
          <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
            <div className="flex items-center gap-2">
              <Badge variant="info">待处理 {reviewResult.total} 条</Badge>
              <Badge variant="success">AI 处理 {reviewResult.processed}</Badge>
              <Badge variant="default">保留人工 {reviewResult.kept}</Badge>
            </div>
            {reviewResult.items.map((item) => (
              <div key={item.request_id} className="flex items-center gap-3 rounded-card border border-border bg-bg-primary p-3">
                {item.action === 'keep' ? (
                  <MinusCircle size={16} className="text-text-muted flex-shrink-0" />
                ) : (
                  <CheckCircle2 size={16} className="text-accent-blue flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-caption text-text-primary font-mono truncate">{item.request_id}</p>
                  <p className="text-caption text-text-muted mt-0.5">{item.reason}</p>
                </div>
                <Badge variant={actionVariant[item.action] || 'default'}>
                  {item.action === 'approve' ? '自动批准' : item.action === 'reject' ? '自动驳回' : '保留人工'}
                </Badge>
              </div>
            ))}
          </div>
        )}

        {rulesResult && (
          <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="info">历史 {rulesResult.stats.total} 条</Badge>
              <Badge variant="critical">严重 {rulesResult.stats.critical}</Badge>
              <Badge variant="high">高 {rulesResult.stats.high}</Badge>
              <Badge variant="medium">中 {rulesResult.stats.medium}</Badge>
              <Badge variant="low">低 {rulesResult.stats.low}</Badge>
              <Badge variant="default">{rulesResult.source === 'llm' ? 'LLM 生成' : '策略生成'}</Badge>
            </div>
            {rulesResult.suggestions.map((s) => (
              <div key={s.rule_name} className="rounded-card border border-border bg-bg-primary p-3 space-y-1.5">
                <div className="flex items-center gap-2">
                  <Wand2 size={14} className="text-accent-blue flex-shrink-0" />
                  <p className="text-caption font-medium text-text-primary flex-1 truncate">{s.rule_name}</p>
                  <Badge variant={actionVariant[s.action] || 'default'}>{s.action}</Badge>
                  <Badge variant="default">优先级 {s.priority}</Badge>
                </div>
                <p className="text-caption text-text-secondary font-mono">
                  {s.condition.field} {s.condition.operator} {s.condition.value}
                </p>
                <p className="text-caption text-text-muted">{s.reason}</p>
                {rulesResult.applied.includes(s.rule_name) && (
                  <Badge variant="success">已应用</Badge>
                )}
              </div>
            ))}
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
          <Button variant="ghost" onClick={handleClose} disabled={running}>
            关闭
          </Button>
          <Button onClick={handleRun} disabled={running} loading={running}>
            {!running && <Sparkles size={16} />}
            {running ? 'AI 执行中...' : meta.runLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
