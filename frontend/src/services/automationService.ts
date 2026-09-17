import { post } from './api';

export interface AutoAnalysisItem {
  raw_data_id: string;
  source_id: string;
  status: 'completed' | 'failed';
  risk_level?: string | null;
  risk_score?: number | null;
  decision?: string | null;
  error?: string;
}

export interface AutoAnalysisResult {
  total: number;
  completed: number;
  failed: number;
  items: AutoAnalysisItem[];
}

export interface AutoReviewItem {
  request_id: string;
  action: 'approve' | 'reject' | 'keep';
  reason: string;
}

export interface AutoReviewResult {
  total: number;
  processed: number;
  kept: number;
  items: AutoReviewItem[];
}

export interface RuleSuggestion {
  rule_name: string;
  condition: { field: string; operator: string; value: string };
  action: string;
  priority: number;
  reason: string;
}

export interface AutoRulesResult {
  stats: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    high_critical_count: number;
    top_tags: string[];
  };
  suggestions: RuleSuggestion[];
  applied: string[];
  source: 'llm' | 'fallback';
}

// AI 自动化含多次 LLM 推理（本地 Ollama 单次 15s+），给足超时
const AUTOMATION_TIMEOUT_MS = 600_000; // 10 分钟

export const automationService = {
  runAnalysis: (maxItems: number) => post<AutoAnalysisResult>('/automation/run-analysis', { max_items: maxItems }, AUTOMATION_TIMEOUT_MS),
  runReview: (confidenceThreshold: number) => post<AutoReviewResult>('/automation/run-review', { confidence_threshold: confidenceThreshold }, AUTOMATION_TIMEOUT_MS),
  runRules: (apply: boolean) => post<AutoRulesResult>('/automation/run-rules', { apply }, AUTOMATION_TIMEOUT_MS),
};
