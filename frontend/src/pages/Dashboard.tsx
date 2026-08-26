import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, AlertTriangle, ArrowRight, Clock3, Database, GitBranch,
  RefreshCw, Scale, ShieldAlert, Sparkles, TrendingUp,
} from 'lucide-react';
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatePanel } from '@/components/ui/StatePanel';
import Empty from '@/components/Empty';
import { dashboardService } from '@/services/dashboardService';
import type { AlertItem, DashboardSummary, RiskTrendPoint } from '@/types/models';

const riskColors = { critical: '#dc2626', high: '#ea580c', medium: '#d97706', low: '#059669' };

function MetricCard({ label, value, note, icon, tone = 'blue' }: {
  label: string; value: number; note: string; icon: React.ReactNode; tone?: 'blue' | 'red' | 'amber' | 'violet';
}) {
  const tones = {
    blue: 'bg-accent-blue/10 text-accent-blue', red: 'bg-risk-critical/10 text-risk-critical',
    amber: 'bg-risk-medium/10 text-risk-medium', violet: 'bg-accent-purple/10 text-accent-purple',
  };
  return (
    <Card className="relative overflow-hidden">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-caption font-medium text-text-secondary">{label}</p>
          <p className="mt-2 font-mono text-[32px] font-bold leading-none tabular-nums text-text-primary">{value}</p>
          <p className="mt-3 text-caption text-text-muted">{note}</p>
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${tones[tone]}`}>{icon}</div>
      </div>
    </Card>
  );
}

function DashboardSkeleton() {
  return <div className="space-y-5">
    <Skeleton className="h-20 w-full" />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[1,2,3,4].map(i => <Skeleton key={i} className="h-36 w-full" />)}</div>
    <div className="grid gap-4 xl:grid-cols-3"><Skeleton className="h-80 w-full xl:col-span-2" /><Skeleton className="h-80 w-full" /></div>
  </div>;
}

export function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [trends, setTrends] = useState<RiskTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState({ summary: false, alerts: false, trends: false });

  const fetchData = useCallback(async () => {
    setLoading(true);
    const [summaryResult, alertResult, trendResult] = await Promise.allSettled([
      dashboardService.getSummary(), dashboardService.getAlerts(8), dashboardService.getTrends(30),
    ]);
    if (summaryResult.status === 'fulfilled') setSummary(summaryResult.value.data);
    else setSummary(null);
    if (alertResult.status === 'fulfilled') setAlerts(alertResult.value.data || []);
    else setAlerts([]);
    if (trendResult.status === 'fulfilled') setTrends(trendResult.value.data || []);
    else setTrends([]);
    setErrors({
      summary: summaryResult.status === 'rejected',
      alerts: alertResult.status === 'rejected',
      trends: trendResult.status === 'rejected',
    });
    setLoading(false);
  }, []);

  useEffect(() => { void fetchData(); }, [fetchData]);
  if (loading) return <DashboardSkeleton />;

  const degraded = errors.summary || errors.alerts || errors.trends;
  const highPriority = summary ? summary.critical_count + summary.high_count : 0;
  const updatedAt = summary?.last_updated ? new Date(summary.last_updated).toLocaleString('zh-CN', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' }) : '暂无';

  return (
    <div className="space-y-5 animate-fade-in">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-caption font-semibold text-accent-blue"><Activity size={14} />风险态势中心</div>
          <h1 className="text-h1 text-text-primary">供应链风险态势</h1>
          <p className="mt-1 text-body text-text-secondary">聚焦需要立即研判和处置的风险事件</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={degraded ? 'high' : 'success'} dot>{degraded ? '部分数据不可用' : '数据服务正常'}</Badge>
          <span className="text-caption text-text-muted">更新于 {updatedAt}</span>
          <Button variant="outline" size="sm" onClick={fetchData}><RefreshCw size={14} />刷新</Button>
        </div>
      </section>

      {errors.summary ? (
        <StatePanel title="风险态势暂时不可用" description="无法获取核心指标。为避免误判，系统不会用零值代替真实风险数据。" onRetry={fetchData} />
      ) : summary && (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="风险事件总量" value={summary.total_risks} note={`其中中低风险 ${summary.medium_count + summary.low_count} 项`} icon={<ShieldAlert size={20}/>} />
          <MetricCard label="重大与高风险" value={highPriority} note={`重大 ${summary.critical_count} · 高风险 ${summary.high_count}`} icon={<TrendingUp size={20}/>} tone="red" />
          <MetricCard label="待审批决策" value={summary.pending_decisions} note="需要决策人完成研判" icon={<Clock3 size={20}/>} tone="amber" />
          <MetricCard label="生效风险规则" value={summary.active_rules} note="覆盖当前自动识别策略" icon={<GitBranch size={20}/>} tone="violet" />
        </section>
      )}

      {summary && summary.total_risks === 0 && !errors.summary ? (
        <Card>
          <Empty title="当前尚未发现风险事件" description="接入或录入供应链数据后，系统会在这里展示风险态势与处置建议。" icon={<Database size={24}/>} action={<Button onClick={() => navigate('/raw-data')}>接入数据源<ArrowRight size={15}/></Button>} />
        </Card>
      ) : (
        <section className="grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2" padding="lg">
            <div className="mb-5 flex items-center justify-between">
              <div><h2 className="text-h3 text-text-primary">30 天风险趋势</h2><p className="mt-1 text-caption text-text-muted">按风险等级观察事件变化</p></div>
              <Badge variant="default">近 30 天</Badge>
            </div>
            {errors.trends ? <StatePanel compact title="趋势数据加载失败" description="核心指标不受影响，可单独重试趋势数据。" onRetry={fetchData} /> : trends.length === 0 ? <Empty compact title="暂无趋势数据" description="产生分析结果后将自动形成趋势。" /> : (
              <div className="h-64"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trends} margin={{top:8,right:8,left:-24,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false}/><XAxis dataKey="date" stroke="var(--color-text-muted)" fontSize={11}/><YAxis stroke="var(--color-text-muted)" fontSize={11}/><Tooltip/><Area type="monotone" dataKey="critical" stroke={riskColors.critical} fill={riskColors.critical} fillOpacity={0.08} strokeWidth={2}/><Area type="monotone" dataKey="high" stroke={riskColors.high} fill={riskColors.high} fillOpacity={0.06} strokeWidth={2}/>
              </AreaChart></ResponsiveContainer></div>
            )}
          </Card>

          <Card padding="lg">
            <div className="mb-5 flex items-center justify-between"><div><h2 className="text-h3 text-text-primary">重大风险队列</h2><p className="mt-1 text-caption text-text-muted">优先处理最新告警</p></div><Button variant="ghost" size="sm" onClick={() => navigate('/analysis')}>全部<ArrowRight size={14}/></Button></div>
            {errors.alerts ? <StatePanel compact title="告警数据加载失败" description="暂时无法确认最新风险事件。" onRetry={fetchData}/> : alerts.length === 0 ? <Empty compact title="暂无风险告警" description="新告警会按照严重程度出现在这里。" /> : <div className="space-y-2">
              {alerts.slice(0,5).map(alert => <button key={alert.id} onClick={() => navigate(`/analysis/${alert.id}`)} className="w-full rounded-btn border border-border/70 p-3 text-left transition-colors hover:border-accent-blue/40 hover:bg-bg-tertiary/30">
                <div className="flex items-start gap-3"><span className={`mt-1 h-2 w-2 flex-none rounded-full ${alert.type === 'critical' ? 'bg-risk-critical' : alert.type === 'high' ? 'bg-risk-high' : 'bg-risk-medium'}`}/><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><p className="truncate text-body font-semibold text-text-primary">{alert.title}</p><span className="whitespace-nowrap text-[11px] text-text-muted">{new Date(alert.created_at).toLocaleDateString('zh-CN')}</span></div><p className="mt-1 line-clamp-2 text-caption text-text-secondary">{alert.description}</p></div></div>
              </button>)}
            </div>}
          </Card>
        </section>
      )}

      <section>
        <div className="mb-3 flex items-end justify-between"><div><h2 className="text-h3 text-text-primary">快速开始</h2><p className="mt-1 text-caption text-text-muted">从数据到决策的核心工作流</p></div></div>
        <div className="grid gap-3 sm:grid-cols-3">
          {[{title:'录入风险数据',desc:'接入供应商、库存或物流信息',path:'/raw-data',icon:<Database size={19}/>,color:'text-accent-blue bg-accent-blue/10'},{title:'启动 AI 风险分析',desc:'识别异常并生成风险证据',path:'/analysis',icon:<Sparkles size={19}/>,color:'text-accent-purple bg-accent-purple/10'},{title:'处理待审批决策',desc:'查看建议、依据与处置动作',path:'/decisions',icon:<Scale size={19}/>,color:'text-risk-medium bg-risk-medium/10'}].map(item => <button key={item.path} onClick={() => navigate(item.path)} className="group flex items-center gap-3 rounded-card border border-border bg-bg-secondary p-4 text-left transition-colors hover:border-accent-blue/40 hover:bg-bg-tertiary/20"><span className={`flex h-10 w-10 items-center justify-center rounded-xl ${item.color}`}>{item.icon}</span><span className="min-w-0 flex-1"><span className="block text-body font-semibold text-text-primary">{item.title}</span><span className="mt-0.5 block text-caption text-text-muted">{item.desc}</span></span><ArrowRight size={16} className="text-text-muted transition-transform group-hover:translate-x-1 group-hover:text-accent-blue"/></button>)}
        </div>
      </section>
      {degraded && <div className="flex items-center gap-2 text-caption text-risk-high"><AlertTriangle size={14}/>部分模块未加载完成，请以模块内错误状态为准。</div>}
    </div>
  );
}
