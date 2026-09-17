import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, Database, Loader2 } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import { useToastStore } from '@/stores/toastStore';
import { dataService } from '@/services/dataService';
import { analysisService } from '@/services/analysisService';
import type { AnalysisResult, RawData } from '@/types/models';

interface NewAnalysisModalProps {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
}

const statusLabel: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
};

/**
 * 新建分析：选择一条原始数据 → 运行 Agent 分析流水线 → 展示结果。
 * 分析含多次 LLM 推理，耗时可达数分钟，提交后保持 loading 态直至返回。
 */
export function NewAnalysisModal({ open, onClose, onDone }: NewAnalysisModalProps) {
  const [items, setItems] = useState<RawData[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [selectedId, setSelectedId] = useState('');
  const [force, setForce] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const { addToast } = useToastStore();

  // 打开时拉取原始数据列表（含已完成项：勾选"重新分析"可覆盖）
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoadingList(true);
    setError('');
    setResult(null);
    setSelectedId('');
    setForce(false);
    dataService
      .list({ page: 1, page_size: 100 })
      .then((res) => {
        if (!cancelled) setItems(res?.items || []);
      })
      .catch(() => {
        if (!cancelled) setError('原始数据列表加载失败，请检查后端服务');
      })
      .finally(() => {
        if (!cancelled) setLoadingList(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const handleRun = useCallback(async () => {
    if (!selectedId) return;
    setRunning(true);
    setError('');
    setResult(null);
    try {
      const res = await analysisService.run(selectedId, force);
      const data = (res?.data ?? null) as AnalysisResult | null;
      if (!data?.request_id) {
        throw new Error('empty');
      }
      setResult(data);
      addToast({
        type: 'success',
        title: '分析完成',
        message: `风险等级 ${data.risk_level}，评分 ${(Number(data.risk_score) * 100).toFixed(0)}`,
      });
      onDone();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string | { message?: string } } } };
      let msg = '分析执行失败，请稍后重试';
      if (axiosErr.response?.status === 404) {
        msg = '原始数据不存在或已被删除';
      } else if (axiosErr.response?.status === 422) {
        msg = '数据质量不满足分析条件（数据可能已被标记为无效）';
      } else if (axiosErr.response?.data?.detail) {
        const detail = axiosErr.response.data.detail;
        msg = typeof detail === 'string' ? detail : detail.message || msg;
      } else if (axiosErr.response?.status === 500) {
        msg = 'Agent 分析流程异常，请检查系统设置中的 LLM 配置';
      }
      setError(msg);
      addToast({ type: 'error', title: '分析失败', message: msg });
    } finally {
      setRunning(false);
    }
  }, [selectedId, force, addToast, onDone]);

  const selected = items.find((it) => it.id === selectedId);

  return (
    <Modal open={open} onClose={onClose} title="新建风险分析" size="md">
      <div className="space-y-4">
        {/* 说明 */}
        <div className="flex items-start gap-3 rounded-card border border-accent-amber/30 bg-accent-amber/10 p-3">
          <Database size={18} className="mt-0.5 flex-shrink-0 text-accent-amber" />
          <p className="text-caption text-text-secondary">
            选择一条供应链数据，系统将运行 Scout → Analyst → Decider 全链路分析，
            生成风险评分与处置建议。含 LLM 推理，可能需要一分钟以上。
          </p>
        </div>

        {result ? (
          /* 结果展示 */
          <div className="space-y-3 animate-fade-in">
            <div className="flex items-center justify-between rounded-card border border-border bg-bg-primary p-4">
              <div className="flex items-center gap-3">
                <RiskLevelBadge level={result.risk_level} />
                <div>
                  <p className="font-mono text-body font-semibold tabular-nums text-text-primary">
                    {(Number(result.risk_score) * 100).toFixed(0)} <span className="text-caption font-normal text-text-muted">/ 100 风险评分</span>
                  </p>
                  <p className="mt-0.5 font-mono text-[11px] text-text-muted">{result.request_id.slice(0, 8)}</p>
                </div>
              </div>
              <Badge variant="success">已完成</Badge>
            </div>
            {result.anomaly_tags && result.anomaly_tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {result.anomaly_tags.map((tag, i) => (
                  <Badge key={i} variant="high">{tag}</Badge>
                ))}
              </div>
            )}
            {result.reasoning && (
              <div className="rounded-card border border-border bg-bg-primary p-3">
                <p className="text-caption font-medium text-text-secondary">分析推理</p>
                <p className="mt-1 line-clamp-4 text-caption text-text-primary">{result.reasoning}</p>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="outline" size="sm" onClick={() => setResult(null)}>再分析一条</Button>
              <Button size="sm" onClick={onClose}>完成<ArrowRight size={14} /></Button>
            </div>
          </div>
        ) : (
          /* 选择与提交 */
          <>
            <div>
              <label htmlFor="analysis-raw-data" className="mb-1.5 block text-caption font-medium text-text-secondary">
                原始数据
              </label>
              {loadingList ? (
                <div className="flex items-center gap-2 rounded-input border border-border bg-bg-primary px-3 py-2.5 text-caption text-text-muted">
                  <Loader2 size={14} className="animate-spin" /> 加载数据列表...
                </div>
              ) : items.length === 0 ? (
                <div className="rounded-input border border-border bg-bg-primary px-3 py-2.5 text-caption text-text-muted">
                  暂无可分析的原始数据，请先到数据中心录入
                </div>
              ) : (
                <select
                  id="analysis-raw-data"
                  value={selectedId}
                  onChange={(e) => setSelectedId(e.target.value)}
                  disabled={running}
                  className="w-full rounded-input px-3 py-2.5 text-body bg-bg-primary border border-border text-text-primary transition-colors focus:outline-none focus:ring-2 focus:ring-accent-amber/50 focus:border-accent-amber hover:border-border-light disabled:opacity-60"
                >
                  <option value="" disabled>选择要分析的数据...</option>
                  {items.map((it) => (
                    <option key={it.id} value={it.id}>
                      {it.source_type} / {it.source_id || it.id.slice(0, 8)} — {statusLabel[it.status] || it.status}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {selected && (
              <div className="rounded-card border border-border bg-bg-primary p-3 text-caption text-text-secondary">
                <div className="flex items-center justify-between">
                  <span>数据状态</span>
                  <Badge variant={selected.status === 'pending' ? 'info' : 'default'}>{statusLabel[selected.status] || selected.status}</Badge>
                </div>
                {selected.updated_at && (
                  <div className="mt-1.5 flex items-center justify-between">
                    <span>上次处理</span>
                    <span className="font-mono tabular-nums">{new Date(selected.updated_at).toLocaleString('zh-CN')}</span>
                  </div>
                )}
              </div>
            )}

            <label className="flex cursor-pointer items-center gap-2 text-caption text-text-secondary select-none">
              <input
                type="checkbox"
                checked={force}
                onChange={(e) => setForce(e.target.checked)}
                disabled={running}
                className="h-4 w-4 rounded border-border accent-[var(--color-accent-amber)]"
              />
              已分析过的数据强制重新分析
            </label>

            {error && (
              <div className="rounded-input border border-risk-critical/20 bg-risk-critical/10 px-3 py-2 text-caption text-risk-critical">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <Button variant="ghost" onClick={onClose} disabled={running}>取消</Button>
              <Button onClick={handleRun} loading={running} disabled={!selectedId}>
                {running ? '分析运行中，请勿关闭' : '开始分析'}
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
