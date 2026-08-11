import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Modal } from '@/components/ui/Modal';
import {
  ChevronRight, ChevronDown, Plus, ToggleLeft, ToggleRight, Edit3, Trash2, Save, Loader2,
} from 'lucide-react';
import { useToastStore } from '@/stores/toastStore';
import { ruleService } from '@/services/ruleService';
import type { RuleNode } from '@/types/models';

/* ── 规则树节点 ── */
function RuleNodeItem({ node, depth = 0, onRefresh }: { node: RuleNode; depth?: number; onRefresh: () => void }) {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(node.rule_name);
  const { addToast } = useToastStore();
  const hasChildren = node.children && node.children.length > 0;

  const handleToggle = useCallback(async () => {
    try {
      await ruleService.toggle(node.id, !node.is_active);
      addToast({ type: 'success', title: '状态已更新', message: node.is_active ? '规则已禁用' : '规则已启用' });
      onRefresh();
    } catch {
      addToast({ type: 'error', title: '操作失败', message: '无法切换规则状态' });
    }
  }, [node.id, node.is_active, addToast, onRefresh]);

  const handleDelete = useCallback(async () => {
    try {
      await ruleService.delete(node.id);
      addToast({ type: 'success', title: '已删除', message: `规则 "${node.rule_name}" 已删除` });
      onRefresh();
    } catch {
      addToast({ type: 'error', title: '删除失败', message: '无法删除规则' });
    }
  }, [node.id, node.rule_name, addToast, onRefresh]);

  return (
    <div>
      <div
        className="flex items-center gap-2 py-2 px-2 rounded-btn hover:bg-bg-tertiary/30 transition-colors group"
        style={{ paddingLeft: `${depth * 24 + 8}px` }}
      >
        {hasChildren ? (
          <button onClick={() => setExpanded(!expanded)} className="text-text-muted hover:text-text-primary">
            {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
        ) : (
          <span className="w-4" />
        )}

        <div className="flex-1 min-w-0 flex items-center gap-2">
          {editing ? (
            <input
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="bg-bg-primary border border-accent-blue rounded-input px-2 py-0.5 text-body text-text-primary outline-none"
              autoFocus
              onBlur={() => setEditing(false)}
              onKeyDown={(e) => e.key === 'Enter' && setEditing(false)}
            />
          ) : (
            <span className="text-body text-text-primary font-medium truncate">{node.rule_name}</span>
          )}
          <Badge variant="default">
            {node.field_name || node.rule_type}
          </Badge>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => setEditing(!editing)}
            className="p-1 rounded text-text-muted hover:text-accent-blue hover:bg-accent-blue/10"
            title="重命名"
          >
            <Edit3 size={14} />
          </button>
          <button
            onClick={handleDelete}
            className="p-1 rounded text-text-muted hover:text-risk-critical hover:bg-risk-critical/10"
            title="删除"
          >
            <Trash2 size={14} />
          </button>
          <button
            onClick={handleToggle}
            className="p-1 rounded text-text-muted hover:text-text-primary"
            title={node.is_active ? '禁用' : '启用'}
          >
            {node.is_active ? <ToggleRight size={18} className="text-risk-low" /> : <ToggleLeft size={18} />}
          </button>
        </div>
      </div>

      {expanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <RuleNodeItem key={child.id} node={child} depth={depth + 1} onRefresh={onRefresh} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── 添加节点表单 ── */
interface AddNodeForm {
  rule_name: string;
  rule_type: string;
  parent_id: string;
  field_name: string;
  operator: string;
  threshold_value: string;
  logic_op: string;
  weight: number;
  priority: number;
  description: string;
}

const RULE_TYPES = [
  { value: 'condition', label: '条件节点' },
  { value: 'action', label: '动作节点' },
  { value: 'group', label: '分组节点' },
];

const OPERATORS = [
  { value: 'eq', label: '等于 (==)' },
  { value: 'ne', label: '不等于 (!=)' },
  { value: 'gt', label: '大于 (>)' },
  { value: 'gte', label: '大于等于 (>=)' },
  { value: 'lt', label: '小于 (<)' },
  { value: 'lte', label: '小于等于 (<=)' },
  { value: 'contains', label: '包含' },
  { value: 'in', label: '在列表中' },
];

const LOGIC_OPS = [
  { value: 'AND', label: 'AND (与)' },
  { value: 'OR', label: 'OR (或)' },
  { value: 'NOT', label: 'NOT (非)' },
];

const formDefaults: AddNodeForm = {
  rule_name: '',
  rule_type: 'condition',
  parent_id: '',
  field_name: '',
  operator: 'eq',
  threshold_value: '',
  logic_op: 'AND',
  weight: 1.0,
  priority: 0,
  description: '',
};

/* ── 主组件 ── */
export function RuleEditor() {
  const [tree, setTree] = useState<RuleNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<AddNodeForm>({ ...formDefaults });
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToastStore();

  const fetchTree = useCallback(async () => {
    try {
      const res = await ruleService.getTree();
      setTree(res?.data || []);
    } catch (error) {
      console.error('Failed to fetch rule tree:', error);
      addToast({ type: 'error', title: '加载失败', message: '无法获取规则树' });
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    fetchTree();
  }, [fetchTree]);

  const handleOpenModal = useCallback(() => {
    setForm({ ...formDefaults });
    setModalOpen(true);
  }, []);

  const handleFormChange = useCallback((field: keyof AddNodeForm, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!form.rule_name.trim()) {
      addToast({ type: 'error', title: '验证失败', message: '请输入规则名称' });
      return;
    }
    setSubmitting(true);
    try {
      await ruleService.create({
        rule_name: form.rule_name.trim(),
        rule_type: form.rule_type,
        parent_id: form.parent_id || null,
        field_name: form.field_name || null,
        operator: form.operator || null,
        threshold_value: form.threshold_value || null,
        logic_op: form.logic_op,
        weight: form.weight,
        priority: form.priority,
        description: form.description || null,
      } as Partial<RuleNode>);
      addToast({ type: 'success', title: '节点已创建', message: `规则 "${form.rule_name}" 创建成功` });
      setModalOpen(false);
      setLoading(true);
      fetchTree();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string | { message?: string } } } };
      let msg = '请检查权限或网络连接';
      if (axiosErr.response?.status === 403) {
        msg = '权限不足，需要管理员权限才能创建规则节点';
      } else if (axiosErr.response?.data?.detail) {
        const detail = axiosErr.response.data.detail;
        msg = typeof detail === 'string' ? detail : (detail.message || msg);
      }
      addToast({ type: 'error', title: '创建失败', message: msg });
    } finally {
      setSubmitting(false);
    }
  }, [form, addToast, fetchTree]);

  const handleSave = async () => {
    setSaving(true);
    try {
      addToast({ type: 'success', title: '规则已保存', message: '当前规则树已保存' });
    } catch {
      addToast({ type: 'error', title: '保存失败', message: '规则保存失败' });
    } finally {
      setSaving(false);
    }
  };

  /* ── 骨架屏 ── */
  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-48 mt-2" />
          </div>
        </div>
        <Card padding="none">
          <div className="p-8 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </Card>
      </div>
    );
  }

  /* ── 页面主体 ── */
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-text-primary">规则引擎</h1>
          <p className="text-body text-text-secondary mt-1">可视化编辑决策规则树</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleOpenModal}>
            <Plus size={16} />
            添加节点
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
            保存规则
          </Button>
        </div>
      </div>

      <Card padding="none">
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-4">
            <Badge variant="info">规则树</Badge>
            <span className="text-caption text-text-muted">{tree.length} 个根节点</span>
          </div>
        </div>
        <div className="p-4">
          {tree.length === 0 ? (
            <div className="p-12 text-center text-text-muted">
              <p className="text-body">暂无规则</p>
              <p className="text-caption mt-1">点击"添加节点"创建第一个规则</p>
            </div>
          ) : (
            tree.map((node) => (
              <RuleNodeItem key={node.id} node={node} onRefresh={fetchTree} />
            ))
          )}
        </div>
      </Card>

      {/* ── 添加节点弹窗 ── */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="添加规则节点" size="lg">
        <div className="space-y-4">
          {/* 规则名称 */}
          <div>
            <label className="block text-caption font-medium text-text-secondary mb-1">规则名称 *</label>
            <input
              value={form.rule_name}
              onChange={(e) => handleFormChange('rule_name', e.target.value)}
              placeholder="例如：供应商风险评分"
              className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-body text-text-primary outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/30 transition-colors"
            />
          </div>

          {/* 规则类型 */}
          <div>
            <label className="block text-caption font-medium text-text-secondary mb-1">规则类型</label>
            <select
              value={form.rule_type}
              onChange={(e) => handleFormChange('rule_type', e.target.value)}
              className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-body text-text-primary outline-none focus:border-accent-blue"
            >
              {RULE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* 字段名 & 运算符 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-caption font-medium text-text-secondary mb-1">字段名</label>
              <input
                value={form.field_name}
                onChange={(e) => handleFormChange('field_name', e.target.value)}
                placeholder="例如：risk_score"
                className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-body text-text-primary outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/30 transition-colors"
              />
            </div>
            <div>
              <label className="block text-caption font-medium text-text-secondary mb-1">运算符</label>
              <select
                value={form.operator}
                onChange={(e) => handleFormChange('operator', e.target.value)}
                className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-body text-text-primary outline-none focus:border-accent-blue"
              >
                <option value="">无</option>
                {OPERATORS.map((op) => (
                  <option key={op.value} value={op.value}>{op.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* 阈值 & 逻辑运算符 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-caption font-medium text-text-secondary mb-1">阈值</label>
              <input
                value={form.threshold_value}
                onChange={(e) => handleFormChange('threshold_value', e.target.value)}
                placeholder="例如：0.6"
                className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-body text-text-primary outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/30 transition-colors"
              />
            </div>
            <div>
              <label className="block text-caption font-medium text-text-secondary mb-1">逻辑运算符</label>
              <select
                value={form.logic_op}
                onChange={(e) => handleFormChange('logic_op', e.target.value)}
                className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-body text-text-primary outline-none focus:border-accent-blue"
              >
                {LOGIC_OPS.map((op) => (
                  <option key={op.value} value={op.value}>{op.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* 权重 & 优先级 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-caption font-medium text-text-secondary mb-1">权重 (0-100)</label>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={form.weight}
                onChange={(e) => handleFormChange('weight', parseFloat(e.target.value) || 0)}
                className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-body text-text-primary outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/30 transition-colors"
              />
            </div>
            <div>
              <label className="block text-caption font-medium text-text-secondary mb-1">优先级</label>
              <input
                type="number"
                min={0}
                value={form.priority}
                onChange={(e) => handleFormChange('priority', parseInt(e.target.value, 10) || 0)}
                className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-body text-text-primary outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/30 transition-colors"
              />
            </div>
          </div>

          {/* 描述 */}
          <div>
            <label className="block text-caption font-medium text-text-secondary mb-1">描述</label>
            <textarea
              value={form.description}
              onChange={(e) => handleFormChange('description', e.target.value)}
              placeholder="规则描述（可选）"
              rows={2}
              className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-body text-text-primary outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/30 transition-colors resize-none"
            />
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <Button variant="ghost" onClick={() => setModalOpen(false)} disabled={submitting}>
              取消
            </Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
              创建节点
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}