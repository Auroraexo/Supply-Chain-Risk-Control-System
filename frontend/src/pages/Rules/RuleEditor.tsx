import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  ChevronRight, ChevronDown, Plus, ToggleLeft, ToggleRight, Edit3, Trash2, Save,
} from 'lucide-react';
import { useToastStore } from '@/stores/toastStore';
import { ruleService } from '@/services/ruleService';
import type { RuleNode } from '@/types/models';

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
  const [tree, setTree] = useState<RuleNode[]>([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToastStore();

  useEffect(() => {
    async function fetchTree() {
      try {
        const res = await ruleService.getTree();
        setTree(res.data);
      } catch (error) {
        console.error('Failed to fetch rule tree:', error);
        addToast({ type: 'error', title: '加载失败', message: '无法获取规则树' });
      } finally {
        setLoading(false);
      }
    }
    fetchTree();
  }, [addToast]);

  const handleSave = async () => {
    try {
      addToast({ type: 'success', title: '规则已保存', message: '规则版本已更新' });
    } catch (error) {
      addToast({ type: 'error', title: '保存失败', message: '规则保存失败' });
    }
  };

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
              <RuleNodeItem key={node.id} node={node} />
            ))
          )}
        </div>
      </Card>
    </div>
  );
}