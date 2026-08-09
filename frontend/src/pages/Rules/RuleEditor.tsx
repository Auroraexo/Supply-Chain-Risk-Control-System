import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  ChevronRight, ChevronDown, Plus, ToggleLeft, ToggleRight, Edit3, Trash2, Save,
} from 'lucide-react';
import { useToastStore } from '@/stores/toastStore';
import type { RuleNode } from '@/types/models';

const initialTree: RuleNode[] = [
  {
    id: 'root',
    rule_name: '风险评估规则',
    rule_type: 'root',
    condition_type: null,
    field_name: null,
    operator: null,
    threshold_value: null,
    logic_op: 'AND',
    weight: 100,
    action: 'evaluate',
    action_params: null,
    priority: 1,
    is_active: true,
    version: 1,
    description: '根节点',
    parent_id: null,
    children: [
      {
        id: 'rule-1',
        rule_name: '供应商风险评估',
        rule_type: 'condition',
        condition_type: 'field',
        field_name: 'source_type',
        operator: 'eq',
        threshold_value: 'supplier',
        logic_op: 'AND',
        weight: 10,
        action: 'check_supplier_risk',
        action_params: null,
        priority: 10,
        is_active: true,
        version: 1,
        description: '检查供应商风险',
        parent_id: 'root',
        children: [
          { id: 'rule-1-1', rule_name: '交货延迟检查', rule_type: 'condition', condition_type: 'field', field_name: 'delay_rate', operator: 'gt', threshold_value: '0.3', logic_op: 'AND', weight: 1, action: 'flag_high_risk', action_params: null, priority: 1, is_active: true, version: 1, description: null, parent_id: 'rule-1', children: [] },
          { id: 'rule-1-2', rule_name: '资质过期检查', rule_type: 'condition', condition_type: 'field', field_name: 'cert_expiry', operator: 'lt', threshold_value: '30', logic_op: 'AND', weight: 1, action: 'flag_medium_risk', action_params: null, priority: 2, is_active: true, version: 1, description: null, parent_id: 'rule-1', children: [] },
        ],
      },
      {
        id: 'rule-2',
        rule_name: '库存风险评估',
        rule_type: 'condition',
        condition_type: 'field',
        field_name: 'source_type',
        operator: 'eq',
        threshold_value: 'inventory',
        logic_op: 'AND',
        weight: 20,
        action: 'check_inventory_risk',
        action_params: null,
        priority: 20,
        is_active: true,
        version: 1,
        description: '检查库存风险',
        parent_id: 'root',
        children: [
          { id: 'rule-2-1', rule_name: '安全库存检查', rule_type: 'condition', condition_type: 'field', field_name: 'quantity', operator: 'lt', threshold_value: 'safety_stock * 0.5', logic_op: 'AND', weight: 1, action: 'flag_critical_risk', action_params: null, priority: 1, is_active: true, version: 1, description: null, parent_id: 'rule-2', children: [] },
        ],
      },
      {
        id: 'rule-3',
        rule_name: '物流风险评估',
        rule_type: 'condition',
        condition_type: 'field',
        field_name: 'source_type',
        operator: 'eq',
        threshold_value: 'logistics',
        logic_op: 'AND',
        weight: 30,
        action: 'check_logistics_risk',
        action_params: null,
        priority: 30,
        is_active: false,
        version: 1,
        description: '物流风险检查',
        parent_id: 'root',
        children: [],
      },
    ],
  },
];

function RuleNodeItem({ node, depth = 0 }: { node: RuleNode; depth?: number }) {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(node.rule_name);
  const hasChildren = node.children && node.children.length > 0;

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
          >
            <Edit3 size={14} />
          </button>
          <button className="p-1 rounded text-text-muted hover:text-risk-critical hover:bg-risk-critical/10">
            <Trash2 size={14} />
          </button>
          <button className="p-1 rounded text-text-muted hover:text-text-primary">
            {node.is_active ? <ToggleRight size={18} className="text-risk-low" /> : <ToggleLeft size={18} />}
          </button>
        </div>
      </div>

      {expanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <RuleNodeItem key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export function RuleEditor() {
  const [tree] = useState<RuleNode[]>(initialTree);
  const { addToast } = useToastStore();

  const handleSave = () => {
    addToast({ type: 'success', title: '规则已保存', message: '规则版本已更新' });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-text-primary">规则引擎</h1>
          <p className="text-body text-text-secondary mt-1">可视化编辑决策规则树</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Plus size={16} />
            添加节点
          </Button>
          <Button size="sm" onClick={handleSave}>
            <Save size={16} />
            保存规则
          </Button>
        </div>
      </div>

      <Card padding="none">
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-4">
            <Badge variant="info">当前版本: v2.1.0</Badge>
            <span className="text-caption text-text-muted">最后更新: 2026-08-07 10:00</span>
          </div>
        </div>
        <div className="p-4">
          {tree.map((node) => (
            <RuleNodeItem key={node.id} node={node} />
          ))}
        </div>
      </Card>
    </div>
  );
}