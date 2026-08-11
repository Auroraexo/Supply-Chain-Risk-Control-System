import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Skeleton } from '@/components/ui/Skeleton';
import { Plus, Search, Edit2, Trash2, UserCheck, UserX } from 'lucide-react';
import { userService } from '@/services/userService';
import { useToastStore } from '@/stores/toastStore';
import type { User } from '@/types/models';

const roleLabels: Record<string, string> = {
  admin: '系统管理员',
  analyst: '风险分析师',
  decider: '决策者',
};

const roleColors: Record<string, 'info' | 'default' | 'success'> = {
  admin: 'info',
  analyst: 'default',
  decider: 'success',
};

export function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const { addToast } = useToastStore();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await userService.list({
        search: search || undefined,
        role: roleFilter || undefined,
        page: 1,
        page_size: 50,
      });
      setUsers(res.data.items);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      addToast({ type: 'error', title: '加载失败', message: '无法获取用户列表' });
    } finally {
      setLoading(false);
    }
  }, [search, roleFilter, addToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDelete = async (user: User) => {
    if (!confirm(`确定要删除用户 "${user.username}" 吗？`)) return;
    try {
      await userService.delete(user.id);
      addToast({ type: 'success', title: '删除成功', message: `用户 ${user.username} 已删除` });
      fetchData();
    } catch (error) {
      addToast({ type: 'error', title: '删除失败', message: '用户删除失败，请重试' });
    }
  };

  const handleToggleActive = async (user: User) => {
    try {
      await userService.update(user.id, { is_active: !user.is_active });
      addToast({
        type: 'success',
        title: user.is_active ? '已禁用' : '已启用',
        message: `用户 ${user.username} 已${user.is_active ? '禁用' : '启用'}`,
      });
      fetchData();
    } catch (error) {
      addToast({ type: 'error', title: '操作失败', message: '用户状态更新失败' });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1 max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              placeholder="搜索用户名..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-input bg-bg-primary border border-border text-body text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-blue/50 focus:border-accent-blue"
            />
          </div>
          <Select
            options={[
              { value: '', label: '全部角色' },
              { value: 'admin', label: '系统管理员' },
              { value: 'analyst', label: '风险分析师' },
              { value: 'decider', label: '决策者' },
            ]}
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="w-32"
          />
        </div>
        <Button size="sm" onClick={() => setShowCreateModal(true)}>
          <Plus size={16} />
          创建用户
        </Button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : users.length === 0 ? (
        <Card className="p-12 text-center">
          <UserX size={32} className="mx-auto mb-3 text-text-muted opacity-40" />
          <p className="text-body text-text-muted">暂无用户</p>
          <p className="text-caption text-text-muted mt-1">点击"创建用户"添加第一个用户</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {users.map((user) => (
            <Card key={user.id} className="flex items-center gap-4 py-3 px-4">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-caption font-medium text-white flex-shrink-0">
                {user.username[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-body font-medium text-text-primary">{user.username}</span>
                  <Badge variant={roleColors[user.role] || 'default'}>{roleLabels[user.role] || user.role}</Badge>
                  {!user.is_active && <Badge variant="high">已禁用</Badge>}
                </div>
                <p className="text-caption text-text-muted mt-0.5">{user.email}</p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleToggleActive(user)}
                  title={user.is_active ? '禁用用户' : '启用用户'}
                >
                  {user.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditingUser(user)}
                  title="编辑用户"
                >
                  <Edit2 size={16} />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(user)}
                  title="删除用户"
                  className="text-risk-critical hover:bg-risk-critical/10"
                >
                  <Trash2 size={16} />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchData();
          }}
        />
      )}

      {editingUser && (
        <EditUserModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onSuccess={() => {
            setEditingUser(null);
            fetchData();
          }}
        />
      )}
    </div>
  );
}

function CreateUserModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('analyst');
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToastStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !email || !password) {
      addToast({ type: 'error', title: '请填写完整', message: '用户名、邮箱和密码为必填项' });
      return;
    }
    setSubmitting(true);
    try {
      await userService.create({ username, email, password, role });
      addToast({ type: 'success', title: '创建成功', message: `用户 ${username} 已创建` });
      onSuccess();
    } catch (error: any) {
      const msg = error?.response?.data?.detail || '创建失败，请重试';
      addToast({ type: 'error', title: '创建失败', message: typeof msg === 'string' ? msg : '未知错误' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={true} onClose={onClose} title="创建用户" size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="用户名" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="请输入用户名" required />
        <Input label="邮箱" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="请输入邮箱" required />
        <Input label="密码" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="至少6位字符" required />
        <Select
          label="角色"
          options={[
            { value: 'analyst', label: '风险分析师' },
            { value: 'decider', label: '决策者' },
            { value: 'admin', label: '系统管理员' },
          ]}
          value={role}
          onChange={(e) => setRole(e.target.value)}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose} type="button">取消</Button>
          <Button type="submit" loading={submitting}>创建</Button>
        </div>
      </form>
    </Modal>
  );
}

function EditUserModal({ user, onClose, onSuccess }: { user: User; onClose: () => void; onSuccess: () => void }) {
  const [email, setEmail] = useState(user.email);
  const [role, setRole] = useState(user.role);
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToastStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await userService.update(user.id, { email, role });
      addToast({ type: 'success', title: '更新成功', message: `用户 ${user.username} 已更新` });
      onSuccess();
    } catch (error: any) {
      const msg = error?.response?.data?.detail || '更新失败，请重试';
      addToast({ type: 'error', title: '更新失败', message: typeof msg === 'string' ? msg : '未知错误' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={true} onClose={onClose} title={`编辑用户: ${user.username}`} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-caption font-medium text-text-secondary">用户名</label>
          <input
            type="text"
            value={user.username}
            disabled
            className="rounded-input px-3 py-2 text-body bg-bg-tertiary/50 border border-border text-text-muted cursor-not-allowed"
          />
        </div>
        <Input label="邮箱" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Select
          label="角色"
          options={[
            { value: 'analyst', label: '风险分析师' },
            { value: 'decider', label: '决策者' },
            { value: 'admin', label: '系统管理员' },
          ]}
          value={role}
          onChange={(e) => setRole(e.target.value as 'analyst' | 'decider' | 'admin')}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose} type="button">取消</Button>
          <Button type="submit" loading={submitting}>保存</Button>
        </div>
      </form>
    </Modal>
  );
}
