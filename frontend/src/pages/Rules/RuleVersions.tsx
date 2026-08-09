import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { RuleVersion } from '@/types/models';

const mockVersions: RuleVersion[] = [
  { id: 'v1', rule_id: 'root', version: 3, snapshot: {}, changed_by: 'admin', change_reason: '新增物流风险评估规则', created_at: '2026-08-07T09:00:00Z' },
  { id: 'v2', rule_id: 'root', version: 2, snapshot: {}, changed_by: 'admin', change_reason: '优化供应商风险评估算法', created_at: '2026-08-01T06:00:00Z' },
  { id: 'v3', rule_id: 'root', version: 1, snapshot: {}, changed_by: 'admin', change_reason: '初始版本', created_at: '2026-07-15T10:00:00Z' },
];

export function RuleVersions() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/rules')}>
          <ArrowLeft size={16} />
          返回规则编辑
        </Button>
        <div>
          <h1 className="text-h1 text-text-primary">规则版本管理</h1>
          <p className="text-body text-text-secondary mt-1">查看和管理规则变更历史</p>
        </div>
      </div>

      <div className="space-y-3">
        {mockVersions.map((version, i) => (
          <Card key={version.id} hover className="flex items-center gap-4">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 rounded-full bg-accent-blue/10 flex items-center justify-center">
                <span className="text-body font-mono font-bold text-accent-blue">v{version.version}</span>
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-body font-medium text-text-primary">版本 {version.version}</span>
                {i === 0 && <Badge variant="info" dot>当前</Badge>}
              </div>
              <p className="text-caption text-text-secondary mt-1">{version.change_reason}</p>
              <p className="text-caption text-text-muted mt-1">
                创建: {new Date(version.created_at).toLocaleString('zh-CN')}
              </p>
            </div>
            <Button variant="outline" size="sm">
              查看详情
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}