import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Upload, Download, Trash2, Eye } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { useToastStore } from '@/stores/toastStore';
import type { RawData, DataStatus } from '@/types/models';
import type { TableColumn } from '@/types/common';

const mockData: RawData[] = [
  { id: '1', source_type: 'ERP系统', source_id: 'ERP-001', payload: {}, data_hash: '', status: 'completed', quality_score: 0.95, created_at: '2026-08-07T10:30:00Z', updated_at: '2026-08-07T10:30:00Z', processed_at: null },
  { id: '2', source_type: '供应商API', source_id: 'SUP-002', payload: {}, data_hash: '', status: 'processing', quality_score: null, created_at: '2026-08-07T09:15:00Z', updated_at: '2026-08-07T09:20:00Z', processed_at: null },
  { id: '3', source_type: '物流平台', source_id: 'LOG-003', payload: {}, data_hash: '', status: 'completed', quality_score: 0.88, created_at: '2026-08-07T08:00:00Z', updated_at: '2026-08-07T08:05:00Z', processed_at: null },
  { id: '4', source_type: '手动录入', source_id: '', payload: {}, data_hash: '', status: 'pending', quality_score: null, created_at: '2026-08-06T16:45:00Z', updated_at: '2026-08-06T16:45:00Z', processed_at: null },
  { id: '5', source_type: 'ERP系统', source_id: 'ERP-005', payload: {}, data_hash: '', status: 'failed', quality_score: null, created_at: '2026-08-06T14:20:00Z', updated_at: '2026-08-06T14:21:00Z', processed_at: null },
];

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
  {
    key: 'actions',
    header: '操作',
    render: () => (
      <div className="flex items-center gap-1">
        <button className="p-1.5 rounded-btn text-text-muted hover:text-accent-blue hover:bg-accent-blue/10 transition-colors">
          <Eye size={16} />
        </button>
        <button className="p-1.5 rounded-btn text-text-muted hover:text-risk-critical hover:bg-risk-critical/10 transition-colors">
          <Trash2 size={16} />
        </button>
      </div>
    ),
  },
];

export function RawDataList() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { addToast } = useToastStore();
  const navigate = useNavigate();

  const filtered = mockData.filter((d) => {
    if (search && !d.source_type.toLowerCase().includes(search.toLowerCase())) return false;
    if (statusFilter && d.status !== statusFilter) return false;
    return true;
  });

  const handleCreate = () => {
    setShowCreateModal(false);
    addToast({ type: 'success', title: '数据创建成功', message: '新的原始数据已提交' });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-text-primary">原始数据管理</h1>
          <p className="text-body text-text-secondary mt-1">管理供应链风险分析的原始数据</p>
        </div>
        <div className="flex items-center gap-2">
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
        </div>
      </div>

      <Card padding="none">
        <div className="flex items-center gap-3 p-4 border-b border-border">
          <Input
            placeholder="搜索数据来源..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
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
        <Table
          columns={columns}
          data={filtered}
          keyExtractor={(d) => d.id}
          onRowClick={(row) => navigate(`/raw-data/${row.id}`)}
        />
      </Card>

      <Modal open={showCreateModal} onClose={() => setShowCreateModal(false)} title="录入原始数据" size="lg">
        <div className="space-y-4">
          <Input label="数据来源" placeholder="例如：ERP系统、供应商API" />
          <Select
            label="数据类型"
            options={[
              { value: 'inventory', label: '库存数据' },
              { value: 'supplier', label: '供应商数据' },
              { value: 'logistics', label: '物流数据' },
              { value: 'manual', label: '手动录入' },
            ]}
            placeholder="选择数据类型"
          />
          <div className="flex flex-col gap-1.5">
            <label className="text-caption font-medium text-text-secondary">数据内容 (JSON)</label>
            <textarea
              rows={6}
              placeholder='{"key": "value"}'
              className="rounded-input px-3 py-2 text-body bg-bg-primary border border-border text-text-primary placeholder:text-text-muted resize-none font-mono text-caption focus:outline-none focus:ring-2 focus:ring-accent-blue/50 focus:border-accent-blue"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>取消</Button>
            <Button onClick={handleCreate}>提交</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}