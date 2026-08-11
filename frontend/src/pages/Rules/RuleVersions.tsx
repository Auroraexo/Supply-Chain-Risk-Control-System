import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { ruleService } from '@/services/ruleService';
import type { RuleVersion } from '@/types/models';

export function RuleVersions() {
  const navigate = useNavigate();
  const [versions, setVersions] = useState<RuleVersion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchVersions() {
      try {
        // 获取所有规则的版本（这里简化为获取第一个规则的版本）
        const rulesRes = await ruleService.list({ page: 1, page_size: 1 });
        if (rulesRes.data.items.length > 0) {
          const ruleId = rulesRes.data.items[0].id;
          const res = await ruleService.getVersions(ruleId);
          setVersions(res.data);
        }
      } catch (error) {
        console.error('Failed to fetch rule versions:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchVersions();
  }, []);

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

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : versions.length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-body text-text-muted">暂无版本记录</p>
        </Card>
      ) : (
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
              <Button variant="outline" size="sm">
                查看详情
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}