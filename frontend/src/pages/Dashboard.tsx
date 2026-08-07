import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import {
  AlertTriangle, TrendingUp, Clock, GitBranch, Shield, ArrowRight, Activity, Scale,
} from 'lucide-react';
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
          <p className="text-display font-mono text-text-primary tabular-nums">{value}</p>
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

  const maxVal = Math.max(...data.flatMap((d) => [d.critical, d.high, d.medium, d.low]), 1);
  const height = 180;
  const barWidth = Math.max(8, Math.min(16, 600 / data.length - 4));

  return (
    <div className="h-48 flex items-end gap-1">
      {data.map((point, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1" title={point.date}>
          <div className="w-full flex flex-col-reverse" style={{ height }}>
            {point.critical > 0 && (
              <div className="w-full bg-risk-critical rounded-t-sm transition-all duration-300" style={{ height: `${(point.critical / maxVal) * 100}%`, minHeight: point.critical > 0 ? 3 : 0 }} />
            )}
            {point.high > 0 && (
              <div className="w-full bg-risk-high transition-all duration-300" style={{ height: `${(point.high / maxVal) * 100}%`, minHeight: point.high > 0 ? 3 : 0 }} />
            )}
            {point.medium > 0 && (
              <div className="w-full bg-risk-medium transition-all duration-300" style={{ height: `${(point.medium / maxVal) * 100}%`, minHeight: point.medium > 0 ? 3 : 0 }} />
            )}
            {point.low > 0 && (
              <div className="w-full bg-risk-low rounded-t-sm transition-all duration-300" style={{ height: `${(point.low / maxVal) * 100}%`, minHeight: point.low > 0 ? 3 : 0 }} />
            )}
          </div>
          <span className="text-caption text-text-muted">{point.date.slice(5)}</span>
        </div>
      ))}
    </div>
  );
}

export function Dashboard() {
  const [summary] = useState<DashboardSummary>({
    total_risks: 128,
    critical_count: 3,
    high_count: 12,
    medium_count: 45,
    low_count: 68,
    pending_decisions: 7,
    active_rules: 24,
    last_updated: new Date().toISOString(),
  });
  const [alerts] = useState<AlertItem[]>([
    { id: '1', type: 'critical', title: '供应商A交货延迟', description: '预计延迟7天，影响产线B', created_at: new Date().toISOString() },
    { id: '2', type: 'high', title: '原材料价格波动超阈值', description: '钢材价格上涨15%', created_at: new Date(Date.now() - 3600000).toISOString() },
    { id: '3', type: 'medium', title: '物流时效下降', description: '华东区域平均时效增加2天', created_at: new Date(Date.now() - 7200000).toISOString() },
    { id: '4', type: 'low', title: '库存水平正常', description: '所有仓库库存处于安全线以上', created_at: new Date(Date.now() - 10800000).toISOString() },
    { id: '5', type: 'high', title: '供应商C资质过期', description: 'ISO认证将于30天后到期', created_at: new Date(Date.now() - 14400000).toISOString() },
  ]);
  const [trends] = useState<RiskTrendPoint[]>(
    Array.from({ length: 7 }, (_, i) => ({
      date: new Date(Date.now() - (6 - i) * 86400000).toISOString().slice(0, 10),
      critical: Math.floor(Math.random() * 3),
      high: Math.floor(Math.random() * 5),
      medium: Math.floor(Math.random() * 10),
      low: Math.floor(Math.random() * 15),
    }))
  );

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
          value={summary.total_risks}
          icon={<AlertTriangle size={16} className="text-accent-cyan" />}
          accent="#06B6D4"
          trend={`上次更新: ${new Date(summary.last_updated).toLocaleDateString('zh-CN')}`}
        />
        <StatCard
          label="严重/高风险"
          value={`${summary.critical_count + summary.high_count}`}
          icon={<TrendingUp size={16} className="text-risk-critical" />}
          accent="#EF4444"
          trend={`严重 ${summary.critical_count} · 高 ${summary.high_count}`}
        />
        <StatCard
          label="待处理决策"
          value={summary.pending_decisions}
          icon={<Clock size={16} className="text-risk-medium" />}
          accent="#F59E0B"
        />
        <StatCard
          label="活跃规则"
          value={summary.active_rules}
          icon={<GitBranch size={16} className="text-accent-purple" />}
          accent="#8B5CF6"
        />
      </div>

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