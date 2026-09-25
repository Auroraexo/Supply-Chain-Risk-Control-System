import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/authStore';
import { useToastStore } from '@/stores/toastStore';
import { get, put } from '@/services/api';
import type { DecisionResult } from '@/types/models';

const labels = { open: '待处置', in_progress: '处置中', resolved: '已整改待复核', closed: '已关闭' };
const transitions = { open: ['open', 'in_progress'], in_progress: ['in_progress', 'resolved'], resolved: ['resolved', 'in_progress', 'closed'], closed: ['closed', 'open'] };

export function TreatmentPanel({ decision, onSaved }: { decision: DecisionResult; onSaved: () => void }) {
  const { user } = useAuthStore();
  const { addToast } = useToastStore();
  const canEdit = user?.role === 'admin' || user?.role === 'decider';
  const [status, setStatus] = useState(decision.case_status || 'open');
  const [owner, setOwner] = useState(decision.owner_id || user?.id || '');
  const [owners, setOwners] = useState<{ id: string; username: string }[]>([]);
  const [due, setDue] = useState(decision.due_at ? new Date(decision.due_at+'Z').toLocaleString('sv-SE').slice(0,16).replace(' ', 'T') : '');
  const [resolution, setResolution] = useState(decision.resolution || '');
  const [comment, setComment] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (canEdit) void get<{ id: string; username: string }[]>('/treatment/owners').then(r => setOwners(r.data)).catch(() => addToast({ type: 'error', title: '负责人列表加载失败', message: '请刷新页面重试' }));
  }, [canEdit, addToast]);
  const save = async () => {
    if (!comment.trim()) { addToast({ type: 'error', title: '请填写处置说明' }); return; }
    setSaving(true);
    try {
      await put(`/decision/${decision.id}/treatment`, { status, owner_id: owner || null, due_at: due ? new Date(due).toISOString() : null, resolution, comment, revision: decision.revision });
      addToast({ type: 'success', title: '处置记录已保存' }); onSaved();
    } catch { addToast({ type: 'error', title: '保存失败', message: '请核对状态步骤、负责人、截止时间和整改结果；任务可能已被他人更新。' }); }
    finally { setSaving(false); }
  };
  const overdue = decision.due_at && new Date(decision.due_at+'Z').getTime() < Date.now() && decision.case_status !== 'closed';
  return <Card>
    <h2 className="mb-4 text-h3 text-text-primary">风险处置闭环 {overdue && <span className="text-caption text-risk-critical">已逾期</span>}</h2>
    <p className="mb-4 text-caption text-text-muted">分配负责人 → 实施整改 → 复核结果 → 关闭风险。审批通过不等于风险已关闭。</p>
    {canEdit ? <div className="grid gap-4 sm:grid-cols-2">
      <Select label="处置状态" value={status} onChange={e => setStatus(e.target.value as typeof status)} options={transitions[decision.case_status || 'open'].filter(s => s !== 'open' || decision.case_status !== 'closed' || user?.role === 'admin').map(s => ({ value: s, label: labels[s as keyof typeof labels] }))}/>
      <Select label="负责人" value={owner} onChange={e => setOwner(e.target.value)} options={[{ value: '', label: '请选择负责人' }, ...owners.map(o => ({ value: o.id, label: o.username }))]}/>
      <Input label="截止时间" type="datetime-local" value={due} onChange={e => setDue(e.target.value)}/>
      <Input label="操作说明（必填）" value={comment} onChange={e => setComment(e.target.value)}/>
      <label className="text-caption text-text-secondary sm:col-span-2">整改结果与证据<textarea className="mt-2 w-full rounded-input border border-border bg-bg-primary p-3 text-body text-text-primary" rows={4} value={resolution} onChange={e => setResolution(e.target.value)}/></label>
      <Button onClick={save} loading={saving}>保存处置记录</Button>
    </div> : <p className="text-body text-text-secondary">当前状态：{labels[decision.case_status || 'open']} · 负责人：{decision.owner_id || '未分配'}<br/>{decision.resolution || '尚无整改结果'}</p>}
  </Card>;
}
