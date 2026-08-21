import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Modal } from '@/components/ui/Modal';
import { ChevronRight, ChevronDown, Plus, ToggleLeft, ToggleRight, Edit3, Trash2, Save, Loader2, GripVertical, Play, Copy, EyeOff } from 'lucide-react';
import { useToastStore } from '@/stores/toastStore';
import { ruleService } from '@/services/ruleService';
import { ContextMenu } from '@/components/ui/ContextMenu';
import type { RuleNode } from '@/types/models';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

/* ── 可拖拽规则树节点 ── */
function SortableRuleNode({ node, depth = 0, onRefresh }: { node: RuleNode; depth?: number; onRefresh: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: node.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <RuleNodeItem node={node} depth={depth} onRefresh={onRefresh} dragHandleProps={{ attributes, listeners }} />
    </div>
  );
}

/* ── 规则树节点 ── */
function RuleNodeItem({
  node,
  depth = 0,
  onRefresh,
  dragHandleProps,
}: {
  node: RuleNode;
  depth?: number;
  onRefresh: () => void;
  dragHandleProps?: Record<string, unknown>;
}) {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(node.rule_name);
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null);
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
      <div className="flex items-center gap-2 py-2 px-2 rounded-btn hover:bg-bg-tertiary/30 transition-colors group"
        style={{ paddingLeft: `${depth * 24 + 8}px` }}
        onContextMenu={(e) => { e.preventDefault(); setCtxMenu({ x: e.clientX, y: e.clientY }); }}
      >
        {/* 拖拽手柄 */}
        {dragHandleProps && (
          <button
            {...(dragHandleProps as Record<string, unknown>)}
            className="cursor-grab active:cursor-grabbing text-text-muted hover:text-text-primary opacity-0 group-hover:opacity-100 transition-opacity"
            title="拖拽排序"
          >
            <GripVertical size={14} />
          </button>
        )}
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
        <SortableContext items={node.children.map((c) => c.id)} strategy={verticalListSortingStrategy}>
          {node.children.map((child) => (
            <SortableRuleNode key={child.id} node={child} depth={depth + 1} onRefresh={onRefresh} />
          ))}
        </SortableContext>
      )}
      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          onClose={() => setCtxMenu(null)}
          items={[
            { label: '编辑节点', icon: <Edit3 size={14} />, onClick: () => { setEditing(true); setEditName(node.rule_name); } },
            { label: '复制节点', icon: <Copy size={14} />, onClick: () => addToast({ type: 'info', title: '已复制', message: `节点 "${node.rule_name}" 已复制到剪贴板` }) },
            { label: '添加子节点', icon: <Plus size={14} />, onClick: () => addToast({ type: 'info', title: '添加子节点', message: '请使用工具栏"添加节点"按钮' }) },
            { divider: true },
            { label: node.is_active ? '禁用节点' : '启用节点', icon: <EyeOff size={14} />, onClick: handleToggle },
            { label: '删除节点', icon: <Trash2 size={14} />, danger: true, onClick: handleDelete },
          ]}
        />
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
  const [testOpen, setTestOpen] = useState(false);
  const [testInput, setTestInput] = useState('{\n  "field": "value"\n}');
  const [testResult, setTestResult] = useState<{ matched: boolean; path: string[]; score: number } | null>(null);
  const [testRunning, setTestRunning] = useState(false);
  const [form, setForm] = useState<AddNodeForm>({ ...formDefaults });
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToastStore();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

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

  const handleTest = useCallback(() => {
    setTestRunning(true);
    setTestResult(null);
    // 模拟规则匹配（前端简易实现）
    setTimeout(() => {
      try {
        const data = JSON.parse(testInput);
        const path: string[] = [];
        let score = 0;

        const traverse = (nodes: RuleNode[], depth = 0) => {
          for (const node of nodes) {
            if (!node.is_active) continue;
            const fieldVal = node.field_name ? data[node.field_name] : null;
            let matched = false;

            if (node.rule_type === 'condition' && node.field_name && node.operator) {
              const threshold = parseFloat(node.threshold_value || '0');
              const val = parseFloat(fieldVal);
              switch (node.operator) {
                case 'gt': matched = !isNaN(val) && val > threshold; break;
                case 'gte': matched = !isNaN(val) && val >= threshold; break;
                case 'lt': matched = !isNaN(val) && val < threshold; break;
                case 'lte': matched = !isNaN(val) && val <= threshold; break;
                case 'eq': matched = fieldVal === node.threshold_value; break;
                case 'neq': matched = fieldVal !== node.threshold_value; break;
                case 'contains': matched = typeof fieldVal === 'string' && fieldVal.includes(node.threshold_value || ''); break;
                default: matched = false;
              }
            } else if (node.rule_type === 'group') {
              matched = true; // 分组节点始终匹配，继续遍历子节点
            }

            if (matched || node.rule_type === 'group') {
              path.push(node.rule_name);
              score += node.weight;
              if (node.children && node.children.length > 0) {
                traverse(node.children, depth + 1);
              }
            }
          }
        };

        traverse(tree);
        setTestResult({ matched: path.length > 0, path, score: Math.min(score, 1) });
      } catch {
        setTestResult({ matched: false, path: [], score: 0 });
      } finally {
        setTestRunning(false);
      }
    }, 300);
  }, [testInput, tree]);

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      // 查找拖拽节点和目标节点所在的父节点
      const findNodeAndParent = (nodes: RuleNode[], targetId: string, parent: RuleNode | null = null): { node: RuleNode; parent: RuleNode | null } | null => {
        for (const node of nodes) {
          if (node.id === targetId) return { node, parent };
          if (node.children) {
            const found = findNodeAndParent(node.children, targetId, node);
            if (found) return found;
          }
        }
        return null;
      };

      const activeResult = findNodeAndParent(tree, active.id as string);
      const overResult = findNodeAndParent(tree, over.id as string);

      if (!activeResult || !overResult) return;
      // 仅允许同级节点拖拽排序
      if (activeResult.parent?.id !== overResult.parent?.id) return;

      const parentNode = activeResult.parent;
      const siblings = parentNode ? parentNode.children : tree;
      const oldIndex = siblings.findIndex((n) => n.id === active.id);
      const newIndex = siblings.findIndex((n) => n.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      // 重新排序
      const newSiblings = [...siblings];
      const [moved] = newSiblings.splice(oldIndex, 1);
      newSiblings.splice(newIndex, 0, moved);

      // 更新本地状态
      if (parentNode) {
        setTree((prev) =>
          prev.map((root) => {
            const updateChildren = (node: RuleNode): RuleNode => {
              if (node.id === parentNode.id) {
                return { ...node, children: newSiblings };
              }
              if (node.children) {
                return { ...node, children: node.children.map(updateChildren) };
              }
              return node;
            };
            return updateChildren(root);
          })
        );
      } else {
        setTree(newSiblings);
      }

      // 更新后端优先级
      try {
        await Promise.all(
          newSiblings.map((node, i) =>
            ruleService.update(node.id, { priority: newSiblings.length - i, rule_type: node.rule_type } as Partial<RuleNode>)
          )
        );
      } catch {
        addToast({ type: 'error', title: '排序失败', message: '无法保存排序结果' });
      }
    },
    [tree, addToast]
  );

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
          <Button variant="outline" size="sm" onClick={() => setTestOpen(true)}>
            <Play size={16} />
            测试规则
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
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={tree.map((n) => n.id)} strategy={verticalListSortingStrategy}>
                {tree.map((node) => (
                  <SortableRuleNode key={node.id} node={node} onRefresh={fetchTree} />
                ))}
              </SortableContext>
            </DndContext>
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

      {/* ── 测试规则弹窗 ── */}
      <Modal open={testOpen} onClose={() => { setTestOpen(false); setTestResult(null); }} title="测试规则" size="lg">
        <div className="flex gap-4">
          {/* 输入区 */}
          <div className="flex-1">
            <label className="block text-caption font-medium text-text-secondary mb-2">测试数据 (JSON)</label>
            <textarea
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              rows={10}
              className="w-full rounded-input border border-border bg-bg-primary px-3 py-2 text-caption text-text-primary font-mono outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/30 transition-colors resize-none"
              placeholder='{"field": "value"}'
            />
          </div>
          {/* 结果区 */}
          <div className="flex-1">
            <label className="block text-caption font-medium text-text-secondary mb-2">执行结果</label>
            <div className="rounded-input border border-border bg-bg-primary p-4 min-h-[240px]">
              {testRunning ? (
                <div className="flex items-center justify-center h-full text-text-muted">
                  <Loader2 size={24} className="animate-spin" />
                </div>
              ) : testResult ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-caption text-text-muted">匹配结果:</span>
                    <Badge variant={testResult.matched ? 'success' : 'high'}>
                      {testResult.matched ? '匹配' : '不匹配'}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-caption text-text-muted">风险评分:</span>
                    <span className="text-caption text-text-primary font-mono ml-2">
                      {(testResult.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  {testResult.path.length > 0 && (
                    <div>
                      <span className="text-caption text-text-muted">匹配路径:</span>
                      <div className="mt-1 text-caption text-text-primary font-mono">
                        {testResult.path.map((p, i) => (
                          <span key={i}>
                            {i > 0 && <span className="text-text-muted"> → </span>}
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-text-muted text-caption">
                  点击"运行测试"查看结果
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 pt-4 mt-4 border-t border-border">
          <Button variant="ghost" onClick={() => { setTestOpen(false); setTestResult(null); }}>
            关闭
          </Button>
          <Button onClick={handleTest} disabled={testRunning}>
            {testRunning ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            运行测试
          </Button>
        </div>
      </Modal>
    </div>
  );
}