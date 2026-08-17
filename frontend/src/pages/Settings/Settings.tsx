import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Tabs } from '@/components/ui/Tabs';
import { Skeleton } from '@/components/ui/Skeleton';
import { useToastStore } from '@/stores/toastStore';
import { Save, Cpu, RefreshCw, Bell, Loader2 } from 'lucide-react';
import { settingsService } from '@/services/settingsService';
import type { NotificationChannel } from '@/services/settingsService';
import { UserManagement } from './UserManagement';

const settingsTabs = [
  { key: 'llm', label: '模型配置' },
  { key: 'notifications', label: '通知设置' },
  { key: 'users', label: '用户管理' },
  { key: 'logs', label: '操作日志' },
];

export function LLMConfig() {
  const [config, setConfig] = useState({
    provider: 'openai',
    model: 'gpt-4o-mini',
    api_key: '',
    temperature: 0.7,
    max_tokens: 4096,
    mock_mode: true,
    smart_routing: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const { addToast } = useToastStore();

  useEffect(() => {
    async function fetchConfig() {
      try {
        const res = await settingsService.getLLMConfig();
        if (res.data) {
          setConfig(res.data);
        }
      } catch {
        addToast({ type: 'error', title: '加载失败', message: '无法获取LLM配置' });
      } finally {
        setLoading(false);
      }
    }
    fetchConfig();
  }, [addToast]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await settingsService.updateLLMConfig(config);
      addToast({ type: 'success', title: '配置已保存', message: 'LLM配置更新成功' });
    } catch {
      addToast({ type: 'error', title: '保存失败', message: 'LLM配置保存失败' });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const res = await settingsService.testLLMConnection({
        provider: config.provider,
        model: config.model,
        api_key: config.api_key,
      });
      if (res.data?.success) {
        addToast({ type: 'success', title: '连接测试成功', message: `${res.data.message} (${res.data.latency_ms}ms)` });
      } else {
        addToast({ type: 'error', title: '连接测试失败', message: res.data?.message || '未知错误' });
      }
    } catch {
      addToast({ type: 'error', title: '测试失败', message: '无法连接到LLM服务' });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <div className="space-y-4">
          <Skeleton className="h-6 w-32" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Cpu size={20} className="text-accent-blue" />
          <h3 className="text-h3 text-text-primary">LLM 模型配置</h3>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleTest} disabled={testing}>
            {testing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            测试连接
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            保存
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Select
          label="LLM Provider"
          options={[
            { value: 'openai', label: 'OpenAI' },
            { value: 'azure_openai', label: 'Azure OpenAI' },
            { value: 'anthropic', label: 'Anthropic' },
            { value: 'local', label: '本地模型 (Ollama)' },
          ]}
          value={config.provider}
          onChange={(e) => setConfig({ ...config, provider: e.target.value })}
        />
        <Input
          label="模型名称"
          value={config.model}
          onChange={(e) => setConfig({ ...config, model: e.target.value })}
        />
        <Input
          label="API Key"
          type="password"
          value={config.api_key}
          onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
        />
        <div className="flex flex-col gap-1.5">
          <label className="text-caption font-medium text-text-secondary">
            Temperature ({config.temperature})
          </label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={config.temperature}
            onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
            className="w-full accent-accent-blue"
          />
        </div>
        <Input
          label="Max Tokens"
          type="number"
          value={config.max_tokens}
          onChange={(e) => setConfig({ ...config, max_tokens: parseInt(e.target.value) })}
        />
        <div className="flex flex-col gap-3 pt-2">
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-body text-text-secondary">Mock 模式</span>
            <button
              onClick={() => setConfig({ ...config, mock_mode: !config.mock_mode })}
              className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${config.mock_mode ? 'bg-accent-blue' : 'bg-bg-tertiary'}`}
            >
              <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${config.mock_mode ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </label>
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-body text-text-secondary">智能路由</span>
            <button
              onClick={() => setConfig({ ...config, smart_routing: !config.smart_routing })}
              className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${config.smart_routing ? 'bg-accent-blue' : 'bg-bg-tertiary'}`}
            >
              <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${config.smart_routing ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </label>
        </div>
      </div>
    </Card>
  );
}

export function NotificationSettings() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { addToast } = useToastStore();

  useEffect(() => {
    async function fetchChannels() {
      try {
        const res = await settingsService.getNotificationSettings();
        if (res.data?.channels) {
          setChannels(res.data.channels);
        }
      } catch {
        addToast({ type: 'error', title: '加载失败', message: '无法获取通知设置' });
      } finally {
        setLoading(false);
      }
    }
    fetchChannels();
  }, [addToast]);

  const handleToggle = (id: string) => {
    setChannels((prev) =>
      prev.map((c) => (c.id === id ? { ...c, enabled: !c.enabled } : c))
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await settingsService.updateNotificationSettings({ channels });
      addToast({ type: 'success', title: '通知设置已保存', message: '通知渠道配置已更新' });
    } catch {
      addToast({ type: 'error', title: '保存失败', message: '通知设置保存失败' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <div className="space-y-4">
          <Skeleton className="h-6 w-32" />
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Bell size={20} className="text-accent-blue" />
          <h3 className="text-h3 text-text-primary">通知渠道</h3>
        </div>
        <Button size="sm" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          保存
        </Button>
      </div>

      <div className="space-y-3">
        {channels.map((channel) => (
          <div
            key={channel.id}
            className="flex items-center gap-4 p-4 rounded-btn bg-bg-primary/50 border border-border"
          >
            <div className="flex-1">
              <p className="text-body font-medium text-text-primary">{channel.name}</p>
              <p className="text-caption text-text-muted mt-0.5">{channel.config || '未配置'}</p>
            </div>
            <button
              onClick={() => handleToggle(channel.id)}
              className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
                channel.enabled ? 'bg-accent-blue' : 'bg-bg-tertiary'
              }`}
            >
              <span
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${
                  channel.enabled ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function Settings() {
  const [activeTab, setActiveTab] = useState('llm');

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-h1 text-text-primary">系统设置</h1>
        <p className="text-body text-text-secondary mt-1">配置系统参数与用户管理</p>
      </div>

      <Tabs tabs={settingsTabs} activeKey={activeTab} onChange={setActiveTab} />

      <div className="mt-4">
        {activeTab === 'llm' && <LLMConfig />}
        {activeTab === 'notifications' && <NotificationSettings />}
        {activeTab === 'users' && <UserManagement />}
        {activeTab === 'logs' && (
          <Card>
            <h3 className="text-h3 text-text-primary mb-4">操作日志</h3>
            <div className="space-y-2">
              {[
                { time: '2026-08-07 10:36:00', user: 'admin', action: '审批决策 REQ-001', status: 'success' },
                { time: '2026-08-07 10:00:00', user: 'admin', action: '更新规则版本至 v2.1.0', status: 'success' },
                { time: '2026-08-07 09:15:00', user: 'analyst', action: '提交分析任务 REQ-002', status: 'success' },
              ].map((log, i) => (
                <div key={i} className="flex items-center gap-3 py-2 px-3 rounded-btn bg-bg-primary/50 text-caption">
                  <span className="text-text-muted w-36">{log.time}</span>
                  <span className="text-text-primary font-medium w-20">{log.user}</span>
                  <span className="text-text-secondary flex-1">{log.action}</span>
                  <span className="text-risk-low">✓</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}