import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Cpu, CheckCircle, XCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { RiskLevelBadge } from '@/components/business/RiskLevelBadge';
import type { AnalysisResult, AgentExecutionLog } from '@/types/models';

const mockDetail: AnalysisResult = {
  id: '1',
  request_id: 'REQ-001',
  raw_data_id: '1',
  risk_level: 'high',
  risk_score: 0.82,
  risk_factors: [
    { name: '供应商延迟风险', severity: 'high', description: '供应商A历史交货延迟率超过30%，近3个月平均延迟5天', score: 0.85 },
    { name: '库存水平偏低', severity: 'medium', description: 'SKU-12345当前库存为安全库存的60%', score: 0.55 },
    { name: '物流时效波动', severity: 'medium', description: '华东区域物流时效标准差增加2天', score: 0.50 },
  ],
  confidence: 0.91,
  agent_log: [
    { id: 'log-1', agent_name: 'Scout', action: '数据预处理', input: { raw_data_id: '1' }, output: { fields_parsed: 5, data_valid: true }, duration_ms: 120, status: 'success', error_message: null, created_at: '2026-08-07T10:35:01Z' },
    { id: 'log-2', agent_name: 'Analyst', action: '风险评估', input: { request_id: 'REQ-001' }, output: { risk_level: 'high', risk_score: 0.82 }, duration_ms: 450, status: 'success', error_message: null, created_at: '2026-08-07T10:35:02Z' },
  ],
  status: 'completed',
  created_at: '2026-08-07T10:35:00Z',
  completed_at: '2026-08-07T10:36:00Z',
};

export function AnalysisDetail() {
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
          <h1 className="text-h1 text-text-primary">分析详情</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-body text-text-secondary">{mockDetail.request_id}</span>
            <RiskLevelBadge level={mockDetail.risk_level} />
          </div>
        </div>
      </div>

      {/* Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card glass>
          <p className="text-caption text-text-muted">风险评分</p>
          <p className="text-h1 font-mono text-risk-high mt-1">{(mockDetail.risk_score * 100).toFixed(0)}</p>
          <p className="text-caption text-text-muted mt-1">/100分</p>
        </Card>
        <Card glass>
          <p className="text-caption text-text-muted">置信度</p>
          <div className="mt-2">
            <ProgressBar value={mockDetail.confidence * 100} variant="green" size="lg" showLabel />
          </div>
        </Card>
        <Card glass>
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-text-muted" />
            <p className="text-caption text-text-muted">处理耗时</p>
          </div>
          <p className="text-h3 text-text-primary mt-1 font-mono">
            {mockDetail.completed_at
              ? `${((new Date(mockDetail.completed_at).getTime() - new Date(mockDetail.created_at).getTime()) / 1000).toFixed(1)}s`
              : '进行中'}
          </p>
        </Card>
        <Card glass>
          <div className="flex items-center gap-2">
            <Cpu size={16} className="text-text-muted" />
            <p className="text-caption text-text-muted">风险因子</p>
          </div>
          <p className="text-h3 text-text-primary mt-1 font-mono">{mockDetail.risk_factors.length}</p>
        </Card>
      </div>

      {/* Risk Factors */}
      <Card>
        <h3 className="text-h3 text-text-primary mb-4">风险因子</h3>
        <div className="space-y-3">
          {mockDetail.risk_factors.map((factor, i) => (
            <div key={i} className="flex items-start gap-3 p-3 rounded-btn bg-bg-primary/50 border border-border/30">
              <RiskLevelBadge level={factor.severity} size="sm" />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-body font-medium text-text-primary">{factor.name}</p>
                  <span className="text-caption font-mono text-text-secondary">{(factor.score * 100).toFixed(0)}分</span>
                </div>
                <p className="text-caption text-text-secondary mt-1">{factor.description}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Agent Execution Log */}
      <Card>
        <h3 className="text-h3 text-text-primary mb-4">Agent 执行日志</h3>
        <div className="space-y-0">
          {mockDetail.agent_log.map((log, i) => (
            <div key={log.id} className="flex gap-3 py-3 border-b border-border/30 last:border-b-0">
              <div className="flex-shrink-0 mt-1">
                {log.status === 'success' ? (
                  <CheckCircle size={16} className="text-risk-low" />
                ) : (
                  <XCircle size={16} className="text-risk-critical" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-body font-medium text-text-primary">{log.agent_name}</span>
                  <Badge variant="default">{log.action}</Badge>
                </div>
                <p className="text-caption text-text-muted mt-1">
                  耗时 {log.duration_ms}ms · {new Date(log.created_at).toLocaleTimeString('zh-CN')}
                </p>
                {log.error_message && (
                  <p className="text-caption text-risk-critical mt-1">{log.error_message}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}