import { useCallback, useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatePanel } from '@/components/ui/StatePanel';
import { get, extractPaginated } from '@/services/api';

interface AuditEvent {
  id: string; entity_id: string; action: string; actor: string;
  comment: string | null; created_at: string;
  before: Record<string, unknown> | null; after: Record<string, unknown> | null;
}

export function AuditPanel({ decisionId }: { decisionId?: string }) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const load = useCallback(async () => {
    setLoading(true); setFailed(false);
    try {
      if (decisionId) {
        const res = await get<AuditEvent[]>(`/decision/${decisionId}/history`);
        setEvents(res.data); setTotal(res.data.length);
      } else {
        const res = extractPaginated<AuditEvent>(await get<unknown>('/audit', { page, page_size: 20 }));
        setEvents(res.items); setTotal(res.total);
      }
    } catch { setFailed(true); }
    finally { setLoading(false); }
  }, [decisionId, page]);
  useEffect(() => { void load(); }, [load]);
  return <Card>
    <div className="mb-4 flex items-center justify-between"><h2 className="text-h3 text-text-primary">{decisionId ? '审核与处置历史' : '真实操作日志'}</h2><Button variant="ghost" size="sm" onClick={load} disabled={loading}>刷新</Button></div>
    {loading ? <p className="text-caption text-text-muted">加载中……</p> : failed ? <StatePanel title="审计日志加载失败" description="请检查服务状态或账号权限，然后重试。" onRetry={load}/> : !events.length ? <p className="text-caption text-text-muted">暂无操作记录</p> : <div className="space-y-3">{events.map(e => <div key={e.id} className="rounded-btn border border-border p-3">
      <div className="flex flex-wrap justify-between gap-2 text-caption"><span className="font-semibold text-text-primary">{e.action}</span><time className="text-text-muted">{new Date(e.created_at + (e.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString('zh-CN')}</time></div>
      <p className="mt-1 break-all text-caption text-text-muted">操作者：{e.actor} · 记录：{e.entity_id}</p>
      {e.comment && <p className="mt-2 whitespace-pre-wrap text-body text-text-secondary">{e.comment}</p>}
      <p className="mt-2 break-all text-caption text-text-secondary">{JSON.stringify(e.before)} → {JSON.stringify(e.after)}</p>
    </div>)}</div>}
    {!decisionId && <div className="mt-4 flex items-center justify-between text-caption text-text-muted"><span>共 {total} 条 · 第 {page} 页</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={page === 1 || loading} onClick={() => setPage(p => p-1)}>上一页</Button><Button variant="outline" size="sm" disabled={page*20 >= total || loading} onClick={() => setPage(p => p+1)}>下一页</Button></div></div>}
  </Card>;
}
