import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { RawData } from '@/types/models';

const mockDetail: RawData = {
  id: '1',
  source_type: 'ERP系统',
  source_id: 'ERP-001',
  payload: {
    warehouse: '华东仓A',
    sku: 'SKU-12345',
    quantity: 1500,
    safety_stock: 500,
    lead_time_days: 7,
    supplier: '供应商A',
  },
  data_hash: '',
  status: 'completed',
  quality_score: 0.95,
  created_at: '2026-08-07T10:30:00Z',
  updated_at: '2026-08-07T10:30:00Z',
  processed_at: null,
};

export function RawDataDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
          返回
        </Button>
        <div>
          <h1 className="text-h1 text-text-primary">数据详情</h1>
          <p className="text-body text-text-secondary mt-1">{mockDetail.source_type} · {mockDetail.source_id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <h3 className="text-h3 text-text-primary mb-4">基本信息</h3>
          <dl className="space-y-3">
            {[
              { label: '数据来源', value: mockDetail.source_type },
              { label: '源ID', value: mockDetail.source_id || '-' },
              { label: '数据哈希', value: mockDetail.data_hash || '-' },
              { label: '创建时间', value: new Date(mockDetail.created_at).toLocaleString('zh-CN') },
              { label: '更新时间', value: mockDetail.updated_at ? new Date(mockDetail.updated_at).toLocaleString('zh-CN') : '-' },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <dt className="text-body text-text-muted">{label}</dt>
                <dd className="text-body text-text-primary font-medium">{value}</dd>
              </div>
            ))}
            <div className="flex justify-between">
              <dt className="text-body text-text-muted">状态</dt>
              <dd><Badge variant="success">已完成</Badge></dd>
            </div>
          </dl>
        </Card>

        <Card>
          <h3 className="text-h3 text-text-primary mb-4">数据内容</h3>
          <pre className="bg-bg-primary rounded-input p-4 text-caption text-text-primary font-mono overflow-x-auto">
            {JSON.stringify(mockDetail.payload, null, 2)}
          </pre>
        </Card>
      </div>
    </div>
  );
}