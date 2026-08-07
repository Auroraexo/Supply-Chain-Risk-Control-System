export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'none';

export type DataStatus = 'pending' | 'processing' | 'running' | 'completed' | 'failed';

export type DecisionType = 'auto_approved' | 'auto_rejected' | 'manual_review';

export type DecisionStatus = 'pending' | 'approved' | 'rejected' | 'escalated';

export type UserRole = 'analyst' | 'decider' | 'admin';

export interface RawData {
  id: string;
  request_id: string;
  source: string;
  data_type: string;
  content: Record<string, unknown>;
  status: DataStatus;
  created_at: string;
  updated_at: string;
}

export interface RiskFactor {
  name: string;
  severity: RiskLevel;
  description: string;
  score: number;
}

export interface AgentExecutionLog {
  id: string;
  agent_name: string;
  action: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  duration_ms: number;
  status: 'success' | 'error';
  error_message: string | null;
  created_at: string;
}

export interface AnalysisResult {
  id: string;
  request_id: string;
  raw_data_id: string;
  risk_level: RiskLevel;
  risk_score: number;
  risk_factors: RiskFactor[];
  confidence: number;
  agent_log: AgentExecutionLog[];
  status: DataStatus;
  created_at: string;
  completed_at: string | null;
}

export interface DecisionResult {
  id: string;
  request_id: string;
  analysis_result_id: string;
  decision_type: DecisionType;
  status: DecisionStatus;
  reason: string;
  rule_node_id: string | null;
  reviewer_id: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface RuleNode {
  id: string;
  name: string;
  condition: string;
  action: string;
  priority: number;
  enabled: boolean;
  children: RuleNode[];
}

export interface RuleVersion {
  id: string;
  version: string;
  rule_tree: RuleNode;
  changelog: string;
  published: boolean;
  published_at: string | null;
  created_at: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface DashboardSummary {
  total_risks: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  pending_decisions: number;
  active_rules: number;
  last_updated: string;
}

export interface RiskTrendPoint {
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface AlertItem {
  id: string;
  type: RiskLevel;
  title: string;
  description: string;
  created_at: string;
}

export interface LLMConfig {
  provider: string;
  model: string;
  api_key: string;
  temperature: number;
  max_tokens: number;
  mock_mode: boolean;
  smart_routing: boolean;
}