import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import { Skeleton } from '@/components/ui/Skeleton';
import { CountUp } from '@/components/ui/CountUp';
import { RingProgress } from '@/components/ui/RingProgress';
import {
  AlertTriangle, TrendingUp, Clock, GitBranch, Shield, ArrowRight, Activity, Scale,
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { dashboardService } from '@/services/dashboardService';
import type { DashboardSummary, RiskTrendPoint, AlertItem } from '@/types/models';

function StatCard({
  label,
  value,
  icon,
  accent,
  trend,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  accent: string;
  trend?: string;
}) {
  return (
    <Card hover glass className="relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-24 h-24 opacity-5 group-hover:opacity-10 transition-opacity" style={{ background: accent }}>
        <div className="w-full h-full rounded-full transform translate-x-1/2 -translate-y-1/2" style={{ background: `radial-gradient(circle, ${accent}, transparent)` }} />
      </div>
      <div className="flex items-start justify-between">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${accent}20` }}>
              {icon}
            </div>
            <span className="text-caption text-text-muted">{label}</span>
          </div>
          <p className="text-display font-mono text-text-primary tabular-nums">
            {typeof value === 'number' ? <CountUp end={value} duration={1000} /> : value}
          </p>
          {trend && <p className="text-caption text-text-muted">{trend}</p>}
        </div>
      </div>
    </Card>
  );
}

function AlertTimeline({ alerts }: { alerts: AlertItem[] }) {
  return (
    <div className="space-y-0">
      {alerts.map((alert, i) => (
        <div key={alert.id} className="flex gap-3 py-3 border-b border-border/30 last:border-b-0 animate-fade-in" style={{ animationDelay: `${i * 80}ms` }}>
          <div className="relative flex-shrink-0">
            <div className="w-2.5 h-2.5 rounded-full mt-1.5" style={{
              backgroundColor: alert.type === 'critical' ? '#EF4444' : alert.type === 'high' ? '#F97316' : alert.type === 'medium' ? '#F59E0B' : '#10B981',
            }} />
            {i < alerts.length - 1 && <div className="absolute top-4 left-1 w-0.5 h-full bg-border/30" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-body font-medium text-text-primary">{alert.title}</p>
            <p className="text-caption text-text-secondary mt-0.5 line-clamp-1">{alert.description}</p>
            <p className="text-caption text-text-muted mt-1">{new Date(alert.created_at).toLocaleString('zh-CN')}</p>
          </div>
          <RiskLevelBadge level={alert.type} size="sm" />
        </div>
      ))}
    </div>
  );
}

function TrendChart({ data }: { data: RiskTrendPoint[] }) {
  if (data.length === 0) return <div className="h-48 flex items-center justify-center text-text-muted">暂无趋势数据</div>;

  const chartData = data.map((point) => ({
    date: point.date.slice(5),
    critical: point.critical,
    high: point.high,
    medium: point.medium,
    low: point.low,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="criticalGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="highGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#F97316" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#F97316" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="mediumGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="lowGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            fontSize: '12px',
            color: '#F9FAFB',
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: '12px', color: '#9CA3AF' }}
          iconType="circle"
          iconSize={8}
        />
        <Area type="monotone" dataKey="critical" stroke="#EF4444" fill="url(#criticalGrad)" strokeWidth={2} name="严重" />
        <Area type="monotone" dataKey="high" stroke="#F97316" fill="url(#highGrad)" strokeWidth={2} name="高风险" />
        <Area type="monotone" dataKey="medium" stroke="#F59E0B" fill="url(#mediumGrad)" strokeWidth={2} name="中风险" />
        <Area type="monotone" dataKey="low" stroke="#10B981" fill="url(#lowGrad)" strokeWidth={2} name="低风险" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [trends, setTrends] = useState<RiskTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [summaryRes, alertsRes, trendsRes] = await Promise.all([
          dashboardService.getSummary(),
          dashboardService.getAlerts(10),
          dashboardService.getTrends(30),
        ]);
        setSummary(summaryRes.data);
        setAlerts(alertsRes.data);
        setTrends(trendsRes.data);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-48 mt-2" />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} glass>
              <Skeleton className="h-4 w-20 mb-3" />
              <Skeleton className="h-8 w-16" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const defaultSummary: DashboardSummary = {
    total_risks: 0,
    critical_count: 0,
    high_count: 0,
    medium_count: 0,
    low_count: 0,
    pending_decisions: 0,
    active_rules: 0,
    last_updated: null,
  };

  const displaySummary = summary || defaultSummary;
  const lastUpdatedDisplay = displaySummary.last_updated
    ? new Date(displaySummary.last_updated).toLocaleDateString('zh-CN')
    : '暂无数据';

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 text-text-primary">风险总览</h1>
          <p className="text-body text-text-secondary mt-1">供应链风险实时监控与分析</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-input bg-risk-low/10 border border-risk-low/20">
            <span className="w-2 h-2 rounded-full bg-risk-low animate-pulse-dot" />
            <span className="text-caption text-risk-low font-medium">系统运行中</span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="总风险数"
          value={displaySummary.total_risks}
          icon={<AlertTriangle size={16} className="text-accent-cyan" />}
          accent="#06B6D4"
          trend={`上次更新: ${lastUpdatedDisplay}`}
        />
        <StatCard
          label="严重/高风险"
          value={`${displaySummary.critical_count + displaySummary.high_count}`}
          icon={<TrendingUp size={16} className="text-risk-critical" />}
          accent="#EF4444"
          trend={`严重 ${displaySummary.critical_count} · 高 ${displaySummary.high_count}`}
        />
        <StatCard
          label="待处理决策"
          value={displaySummary.pending_decisions}
          icon={<Clock size={16} className="text-risk-medium" />}
          accent="#F59E0B"
        />
        <StatCard
          label="活跃规则"
          value={displaySummary.active_rules}
          icon={<GitBranch size={16} className="text-accent-purple" />}
          accent="#8B5CF6"
        />
      </div>

      {/* Risk Level Rings */}
      {displaySummary.total_risks > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card hover className="flex flex-col items-center py-5">
            <div className="relative inline-flex">
              <RingProgress
                value={displaySummary.critical_count}
                max={displaySummary.total_risks}
                color="#EF4444"
                size={72}
                strokeWidth={5}
              />
            </div>
            <span className="text-caption text-text-muted mt-2">严重</span>
            <span className="text-body font-bold text-risk-critical">{displaySummary.critical_count}</span>
          </Card>
          <Card hover className="flex flex-col items-center py-5">
            <div className="relative inline-flex">
              <RingProgress
                value={displaySummary.high_count}
                max={displaySummary.total_risks}
                color="#F97316"
                size={72}
                strokeWidth={5}
              />
            </div>
            <span className="text-caption text-text-muted mt-2">高风险</span>
            <span className="text-body font-bold text-risk-high">{displaySummary.high_count}</span>
          </Card>
          <Card hover className="flex flex-col items-center py-5">
            <div className="relative inline-flex">
              <RingProgress
                value={displaySummary.medium_count}
                max={displaySummary.total_risks}
                color="#F59E0B"
                size={72}
                strokeWidth={5}
              />
            </div>
            <span className="text-caption text-text-muted mt-2">中风险</span>
            <span className="text-body font-bold text-risk-medium">{displaySummary.medium_count}</span>
          </Card>
          <Card hover className="flex flex-col items-center py-5">
            <div className="relative inline-flex">
              <RingProgress
                value={displaySummary.low_count}
                max={displaySummary.total_risks}
                color="#10B981"
                size={72}
                strokeWidth={5}
              />
            </div>
            <span className="text-caption text-text-muted mt-2">低风险</span>
            <span className="text-body font-bold text-risk-low">{displaySummary.low_count}</span>
          </Card>
        </div>
      )}

      {/* Trend & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2" glass>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-h3 text-text-primary">风险趋势</h3>
            <div className="flex items-center gap-3">
              {[
                { color: 'bg-risk-critical', label: '严重' },
                { color: 'bg-risk-high', label: '高' },
                { color: 'bg-risk-medium', label: '中' },
                { color: 'bg-risk-low', label: '低' },
              ].map(({ color, label }) => (
                <div key={label} className="flex items-center gap-1">
                  <span className={`w-2.5 h-2.5 rounded-sm ${color}`} />
                  <span className="text-caption text-text-muted">{label}</span>
                </div>
              ))}
            </div>
          </div>
          <TrendChart data={trends} />
        </Card>

        <Card glass>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-h3 text-text-primary">最近告警</h3>
            <Badge variant="info" dot>
              <Activity size={12} />
              <span>实时</span>
            </Badge>
          </div>
          <AlertTimeline alerts={alerts} />
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card hover className="group cursor-pointer border-accent-blue/20 hover:border-accent-blue/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center group-hover:bg-accent-blue/20 transition-colors">
              <Shield size={20} className="text-accent-blue" />
            </div>
            <div className="flex-1">
              <p className="text-body font-medium text-text-primary">创建分析任务</p>
              <p className="text-caption text-text-muted">提交数据进行风险评估</p>
            </div>
            <ArrowRight size={18} className="text-text-muted group-hover:text-accent-blue transition-colors" />
          </div>
        </Card>
        <Card hover className="group cursor-pointer border-accent-purple/20 hover:border-accent-purple/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-purple/10 flex items-center justify-center group-hover:bg-accent-purple/20 transition-colors">
              <Scale size={20} className="text-accent-purple" />
            </div>
            <div className="flex-1">
              <p className="text-body font-medium text-text-primary">查看待处理决策</p>
              <p className="text-caption text-text-muted">审批待决策的风险项</p>
            </div>
            <ArrowRight size={18} className="text-text-muted group-hover:text-accent-purple transition-colors" />
          </div>
        </Card>
        <Card hover className="group cursor-pointer border-accent-cyan/20 hover:border-accent-cyan/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-cyan/10 flex items-center justify-center group-hover:bg-accent-cyan/20 transition-colors">
              <GitBranch size={20} className="text-accent-cyan" />
            </div>
            <div className="flex-1">
              <p className="text-body font-medium text-text-primary">管理规则引擎</p>
              <p className="text-caption text-text-muted">配置决策规则与策略</p>
            </div>
            <ArrowRight size={18} className="text-text-muted group-hover:text-accent-cyan transition-colors" />
          </div>
        </Card>
      </div>
    </div>
  );
}