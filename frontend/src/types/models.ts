export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'none';

export type DataStatus = 'pending' | 'processing' | 'running' | 'completed' | 'failed';

export type DecisionType = 'approve' | 'reject' | 'escalate' | 'pending_review';

export type DecisionStatus = 'pending' | 'approved' | 'rejected' | 'escalated';

export type UserRole = 'analyst' | 'decider' | 'admin';

export interface RawData {
  id: string;
  source_type: string;
  source_id: string;
  payload: Record<string, unknown>;
  data_hash: string;
  status: DataStatus;
  quality_score: number | null;
  created_at: string;
  updated_at: string | null;
  processed_at: string | null;
}

export interface RiskFactor {
  name: string;
  severity: RiskLevel;
  description: string;
  score: number;
}

export interface AnalysisResult {
  id: string;
  request_id: string;
  raw_data_id: string;
  risk_level: RiskLevel;
  risk_score: number;
  anomaly_tags: string[] | null;
  reasoning: string | null;
  facts_summary: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
}

export interface DecisionResult {
  id: string;
  request_id: string;
  analysis_id: string;
  decision: DecisionType;
  confidence: number | null;
  explanation: string | null;
  decision_path: string[] | null;
  reflection_passed: boolean | null;
  reviewed_by: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface RuleNode {
  id: string;
  rule_name: string;
  rule_type: string;
  condition_type: string | null;
  field_name: string | null;
  operator: string | null;
  threshold_value: string | null;
  logic_op: string;
  weight: number;
  action: string | null;
  action_params: Record<string, unknown> | null;
  priority: number;
  is_active: boolean;
  version: number;
  description: string | null;
  parent_id: string | null;
  children: RuleNode[];
}

export interface RuleVersion {
  id: string;
  rule_id: string;
  version: number;
  snapshot: Record<string, unknown>;
  changed_by: string | null;
  change_reason: string | null;
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