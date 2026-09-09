import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, GitCompare } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { DiffView } from '@/components/ui/DiffView';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatePanel } from '@/components/ui/StatePanel';
import Empty from '@/components/Empty';
import { ruleService } from '@/services/ruleService';
import type { RuleVersion } from '@/types/models';

export function RuleVersions() {
  const navigate = useNavigate();
  const [versions, setVersions] = useState<RuleVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedLeft, setSelectedLeft] = useState<number | null>(null);
  const [selectedRight, setSelectedRight] = useState<number | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    async function fetchVersions() {
      try {
        // 获取所有规则的版本（这里简化为获取第一个规则的版本）
        const rulesRes = await ruleService.list({ page: 1, page_size: 1 });
        const items = rulesRes?.data?.items || [];
        if (items.length > 0) {
          const ruleId = items[0].id;
          const res = await ruleService.getVersions(ruleId);
          setVersions(res?.data || []);
        }
      } catch (error) {
        console.error('Failed to fetch rule versions:', error);
        setLoadError(true);
      } finally {
        setLoading(false);
      }
    }
    fetchVersions();
  }, []);

  const handleCompare = () => {
    if (selectedLeft !== null && selectedRight !== null) {
      setShowDiff(true);
    }
  };

  const leftVersion = versions.find((_, i) => i === selectedLeft);
  const rightVersion = versions.find((_, i) => i === selectedRight);

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader eyebrow="Policy History" title="规则版本管理" description="查看、选择并对比规则变更历史" actions={<Button variant="ghost" size="sm" onClick={() => navigate('/rules')}><ArrowLeft size={16} />返回规则编辑</Button>} />

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : loadError ? (
        <StatePanel title="无法加载规则版本" description="规则历史服务暂时不可用，请重试。" onRetry={() => window.location.reload()} />
      ) : versions.length === 0 ? (
        <Card><Empty title="暂无版本记录" description="保存规则后，系统会在这里保留可审计的版本快照。" icon={<GitCompare size={24} />} /></Card>
      ) : (
        <div className="space-y-4">
          {/* 版本对比栏 */}
          <Card className="p-4 flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-caption text-text-muted">版本A:</span>
              <select
                value={selectedLeft ?? ''}
                onChange={(e) => { setSelectedLeft(e.target.value ? Number(e.target.value) : null); setShowDiff(false); }}
                className="rounded-input border border-border bg-bg-primary px-2 py-1 text-caption text-text-primary"
              >
                <option value="">选择版本</option>
                {versions.map((v, i) => (
                  <option key={v.id} value={i}>v{v.version} - {new Date(v.created_at).toLocaleDateString('zh-CN')}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-caption text-text-muted">版本B:</span>
              <select
                value={selectedRight ?? ''}
                onChange={(e) => { setSelectedRight(e.target.value ? Number(e.target.value) : null); setShowDiff(false); }}
                className="rounded-input border border-border bg-bg-primary px-2 py-1 text-caption text-text-primary"
              >
                <option value="">选择版本</option>
                {versions.map((v, i) => (
                  <option key={v.id} value={i}>v{v.version} - {new Date(v.created_at).toLocaleDateString('zh-CN')}</option>
                ))}
              </select>
            </div>
            <Button
              size="sm"
              onClick={handleCompare}
              disabled={selectedLeft === null || selectedRight === null || selectedLeft === selectedRight}
            >
              <GitCompare size={14} />
              对比差异
            </Button>
          </Card>

          {/* 差异对比视图 */}
          {showDiff && leftVersion && rightVersion && (
            <Card>
              <div className="p-4 border-b border-border">
                <h3 className="text-h3 text-text-primary">
                  版本对比：v{leftVersion.version} → v{rightVersion.version}
                </h3>
              </div>
              <DiffView
                left={leftVersion.snapshot}
                right={rightVersion.snapshot}
                leftLabel={`v${leftVersion.version} (${new Date(leftVersion.created_at).toLocaleDateString('zh-CN')})`}
                rightLabel={`v${rightVersion.version} (${new Date(rightVersion.created_at).toLocaleDateString('zh-CN')})`}
              />
            </Card>
          )}

          {/* 版本列表 */}
          <div className="space-y-3">
            {versions.map((version, i) => (
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
                  <p className="text-caption text-text-secondary mt-1">{version.change_reason || '无变更说明'}</p>
                  <p className="text-caption text-text-muted mt-1">
                    创建: {new Date(version.created_at).toLocaleString('zh-CN')}
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => { setSelectedLeft(i); setShowDiff(false); }}>
                  {selectedLeft === i ? '已选为版本 A' : '选为版本 A'}
                </Button>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
