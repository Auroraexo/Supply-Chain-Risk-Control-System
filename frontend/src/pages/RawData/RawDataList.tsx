import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Upload, Download, Eye } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Drawer } from '@/components/ui/Drawer';
import { Skeleton } from '@/components/ui/Skeleton';
import { PageHeader } from '@/components/ui/PageHeader';
import Empty from '@/components/Empty';
import { useToastStore } from '@/stores/toastStore';
import { dataService } from '@/services/dataService';
import type { RawData, DataStatus } from '@/types/models';
import type { TableColumn } from '@/types/common';

const statusConfig: Record<DataStatus, { label: string; variant: 'info' | 'success' | 'default' | 'high' }> = {
  pending: { label: '待处理', variant: 'default' },
  processing: { label: '处理中', variant: 'info' },
  running: { label: '运行中', variant: 'info' },
  completed: { label: '已完成', variant: 'success' },
  failed: { label: '失败', variant: 'high' },
};

const columns: TableColumn<RawData>[] = [
  { key: 'source_type', header: '数据来源' },
  { key: 'source_id', header: '源ID', render: (row) => <span>{row.source_id || '-'}</span> },
  {
    key: 'status',
    header: '状态',
    render: (row) => {
      const cfg = statusConfig[row.status];
      return <Badge variant={cfg.variant} dot={row.status === 'processing'}>{cfg.label}</Badge>;
    },
  },
  {
    key: 'created_at',
    header: '创建时间',
    render: (row) => <span className="text-text-secondary">{new Date(row.created_at).toLocaleString('zh-CN')}</span>,
  },
];

export function RawDataList() {
  const [data, setData] = useState<RawData[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [drawerData, setDrawerData] = useState<RawData | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { addToast } = useToastStore();
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await dataService.list({
        search: search || undefined,
        status: statusFilter || undefined,
        page: 1,
        page_size: 50,
      });
      setData(res?.data?.items || []);
    } catch {
      addToast({ type: 'error', title: '加载失败', message: '无法获取数据列表' });
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, addToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = async (formData: { source_type: string; source_id: string; data_type: string; content: string }) => {
    try {
      let payload: Record<string, unknown> = {};
      try { payload = JSON.parse(formData.content); } catch { payload = { content: formData.content }; }

      await dataService.create({
        source_type: formData.source_type,
        source_id: formData.source_id,
        payload,
      });
      setShowCreateModal(false);
      addToast({ type: 'success', title: '数据创建成功', message: '新的原始数据已提交' });
      fetchData();
    } catch {
      addToast({ type: 'error', title: '创建失败', message: '数据提交失败，请重试' });
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader eyebrow="Data Center" title="供应链数据中心" description="管理风险分析所需的供应商、库存与物流数据" actions={<>
          <Button variant="outline" size="sm">
            <Upload size={16} />
            批量导入
          </Button>
          <Button variant="outline" size="sm">
            <Download size={16} />
            导出
          </Button>
          <Button size="sm" onClick={() => setShowCreateModal(true)}>
            <Plus size={16} />
            录入数据
          </Button>
        </>} />

      <Card padding="none">
        <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center">
          <Input
            placeholder="搜索数据来源..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full sm:max-w-xs"
          />
          <Select
            options={[
              { value: '', label: '全部状态' },
              { value: 'pending', label: '待处理' },
              { value: 'processing', label: '处理中' },
              { value: 'completed', label: '已完成' },
              { value: 'failed', label: '失败' },
            ]}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-32"
          />
        </div>
        {loading ? (
          <div className="p-8 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : (
          data.length === 0 ? <Empty title="暂无供应链数据" description="录入或批量导入数据后，可以启动风险识别与分析。" action={<Button size="sm" onClick={() => setShowCreateModal(true)}><Plus size={15}/>录入第一条数据</Button>} /> : <Table
            columns={columns}
            data={data}
            keyExtractor={(d) => d.id}
            onRowClick={(row) => { setDrawerData(row); setDrawerOpen(true); }}
          />
        )}
      </Card>

      <Modal open={showCreateModal} onClose={() => setShowCreateModal(false)} title="录入原始数据" size="lg">
        <CreateDataForm onSubmit={handleCreate} onCancel={() => setShowCreateModal(false)} />
      </Modal>

      <Drawer open={drawerOpen} onClose={() => { setDrawerOpen(false); setDrawerData(null); }} title="数据详情预览">
        {drawerData && (
          <div className="space-y-4">
            <div>
              <h3 className="text-h3 text-text-primary mb-3">基本信息</h3>
              <dl className="space-y-2.5">
                {[
                  { label: '数据来源', value: drawerData.source_type },
                  { label: '源ID', value: drawerData.source_id || '-' },
                  { label: '数据哈希', value: drawerData.data_hash?.slice(0, 16) + '...' || '-' },
                  { label: '质量评分', value: drawerData.quality_score?.toFixed(2) || '-' },
                  { label: '创建时间', value: new Date(drawerData.created_at).toLocaleString('zh-CN') },
                ].map(({ label, value }) => (
                  <div key={label} className="flex justify-between py-1 border-b border-border/20 last:border-b-0">
                    <dt className="text-caption text-text-muted">{label}</dt>
                    <dd className="text-caption text-text-primary font-medium text-right max-w-[200px] truncate">{value}</dd>
                  </div>
                ))}
                <div className="flex justify-between py-1">
                  <dt className="text-caption text-text-muted">状态</dt>
                  <dd>
                    {(() => {
                      const cfg = statusConfig[drawerData.status];
                      return <Badge variant={cfg?.variant || 'default'}>{cfg?.label || drawerData.status}</Badge>;
                    })()}
                  </dd>
                </div>
              </dl>
            </div>
            <div>
              <h3 className="text-h3 text-text-primary mb-3">数据内容</h3>
              <pre className="bg-bg-primary rounded-input p-3 text-caption text-text-primary font-mono overflow-x-auto max-h-64 overflow-y-auto">
                {JSON.stringify(drawerData.payload, null, 2)}
              </pre>
            </div>
            <div className="pt-3 border-t border-border">
              <Button variant="outline" className="w-full" onClick={() => { navigate(`/raw-data/${drawerData.id}`); setDrawerOpen(false); }}>
                <Eye size={16} />
                查看完整详情
              </Button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}

function CreateDataForm({ onSubmit, onCancel }: { onSubmit: (data: { source_type: string; source_id: string; data_type: string; content: string }) => void; onCancel: () => void }) {
  const [sourceType, setSourceType] = useState('');
  const [sourceId, setSourceId] = useState('');
  const [dataType, setDataType] = useState('');
  const [content, setContent] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ source_type: sourceType, source_id: sourceId, data_type: dataType, content });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input label="数据来源" placeholder="例如：ERP系统、供应商API" value={sourceType} onChange={(e) => setSourceType(e.target.value)} required />
      <Input label="源ID" placeholder="例如：ERP-001" value={sourceId} onChange={(e) => setSourceId(e.target.value)} />
      <Select
        label="数据类型"
        options={[
          { value: 'inventory', label: '库存数据' },
          { value: 'supplier', label: '供应商数据' },
          { value: 'logistics', label: '物流数据' },
          { value: 'manual', label: '手动录入' },
        ]}
        value={dataType}
        onChange={(e) => setDataType(e.target.value)}
        placeholder="选择数据类型"
      />
      <div className="flex flex-col gap-1.5">
        <label className="text-caption font-medium text-text-secondary">数据内容 (JSON)</label>
        <textarea
          rows={6}
          placeholder='{"key": "value"}'
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="rounded-input px-3 py-2 text-body bg-bg-primary border border-border text-text-primary placeholder:text-text-muted resize-none font-mono text-caption focus:outline-none focus:ring-2 focus:ring-accent-blue/50 focus:border-accent-blue"
        />
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="secondary" onClick={onCancel}>取消</Button>
        <Button type="submit">提交</Button>
      </div>
    </form>
  );
}
