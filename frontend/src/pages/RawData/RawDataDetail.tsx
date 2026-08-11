import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { dataService } from '@/services/dataService';
import type { RawData } from '@/types/models';

const statusConfig: Record<string, { label: string; variant: 'info' | 'success' | 'default' | 'high' }> = {
  pending: { label: '待处理', variant: 'default' },
  processing: { label: '处理中', variant: 'info' },
  completed: { label: '已完成', variant: 'success' },
  failed: { label: '失败', variant: 'high' },
};

export function RawDataDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<RawData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      if (!id) return;
      try {
        const res = await dataService.getById(id);
        setData(res.data);
      } catch (error) {
        console.error('Failed to fetch raw data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-20" />
          <div>
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-48 mt-2" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <Card key={i}>
              <Skeleton className="h-6 w-32 mb-4" />
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((j) => (
                  <Skeleton key={j} className="h-4 w-full" />
                ))}
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
          返回
        </Button>
        <Card className="p-12 text-center">
          <p className="text-body text-text-muted">数据不存在</p>
        </Card>
      </div>
    );
  }

  const statusCfg = statusConfig[data.status] || { label: data.status, variant: 'default' as const };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
          返回
        </Button>
        <div>
          <h1 className="text-h1 text-text-primary">数据详情</h1>
          <p className="text-body text-text-secondary mt-1">{data.source_type} · {data.source_id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <h3 className="text-h3 text-text-primary mb-4">基本信息</h3>
          <dl className="space-y-3">
            {[
              { label: '数据来源', value: data.source_type },
              { label: '源ID', value: data.source_id || '-' },
              { label: '数据哈希', value: data.data_hash || '-' },
              { label: '创建时间', value: new Date(data.created_at).toLocaleString('zh-CN') },
              { label: '更新时间', value: data.updated_at ? new Date(data.updated_at).toLocaleString('zh-CN') : '-' },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <dt className="text-body text-text-muted">{label}</dt>
                <dd className="text-body text-text-primary font-medium">{value}</dd>
              </div>
            ))}
            <div className="flex justify-between">
              <dt className="text-body text-text-muted">状态</dt>
              <dd><Badge variant={statusCfg.variant}>{statusCfg.label}</Badge></dd>
            </div>
          </dl>
        </Card>

        <Card>
          <h3 className="text-h3 text-text-primary mb-4">数据内容</h3>
          <pre className="bg-bg-primary rounded-input p-4 text-caption text-text-primary font-mono overflow-x-auto">
            {JSON.stringify(data.payload, null, 2)}
          </pre>
        </Card>
      </div>
    </div>
  );
}