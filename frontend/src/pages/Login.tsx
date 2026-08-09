import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { useAuthStore } from '@/stores/authStore';
import { useToastStore } from '@/stores/toastStore';
import { authService } from '@/services/authService';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const { addToast } = useToastStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username || !password) {
      setError('请输入用户名和密码');
      return;
    }

    setLoading(true);
    try {
      const response = await authService.login({ username, password });
      const { access_token, user } = response.data;
      localStorage.setItem('auth_token', access_token);
      login(
        {
          id: user.id,
          username: user.username,
          email: '',
          role: user.role as 'analyst' | 'decider' | 'admin',
          is_active: true,
          created_at: '',
        },
        access_token
      );
      addToast({ type: 'success', title: '登录成功', message: '欢迎回来' });
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message
        || (err as { response?: { data?: { message?: string } } })?.response?.data?.message
        || '登录失败，请检查用户名和密码';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-accent-blue/5 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-accent-purple/5 blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full border border-border/20" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full border border-border/10" />
      </div>

      <Card className="w-full max-w-md relative z-10 p-0 overflow-hidden" glass>
        {/* Header */}
        <div className="px-8 pt-8 pb-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center mx-auto mb-4 shadow-glow-blue">
            <Shield size={28} className="text-white" />
          </div>
          <h1 className="text-h2 text-text-primary">供应链风险控制系统</h1>
          <p className="text-body text-text-secondary mt-2">Supply Chain Risk Control System</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-8 pb-8 space-y-4">
          {error && (
            <div className="px-3 py-2 rounded-input bg-risk-critical/10 border border-risk-critical/20 text-caption text-risk-critical">
              {error}
            </div>
          )}

          <Input
            label="用户名"
            placeholder="请输入用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />

          <div className="flex flex-col gap-1.5">
            <label className="text-caption font-medium text-text-secondary">密码</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="请输入密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="w-full rounded-input px-3 py-2 pr-10 text-body bg-bg-primary border border-border text-text-primary placeholder:text-text-muted transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-accent-blue/50 focus:border-accent-blue hover:border-border-light"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <Button type="submit" loading={loading} className="w-full" size="lg">
            登录
          </Button>

          <div className="flex items-center gap-2 text-caption text-text-muted justify-center">
            <span>测试账号：</span>
            <code className="px-1.5 py-0.5 rounded bg-bg-tertiary text-accent-blue font-mono">admin</code>
            <span>或</span>
            <code className="px-1.5 py-0.5 rounded bg-bg-tertiary text-accent-cyan font-mono">analyst</code>
          </div>
        </form>
      </Card>
    </div>
  );
}