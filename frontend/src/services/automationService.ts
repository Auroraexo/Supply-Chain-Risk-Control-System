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

export const automationService = {
  runAnalysis: (maxItems: number) => post<AutoAnalysisResult>('/automation/run-analysis', { max_items: maxItems }),
  runReview: (confidenceThreshold: number) => post<AutoReviewResult>('/automation/run-review', { confidence_threshold: confidenceThreshold }),
  runRules: (apply: boolean) => post<AutoRulesResult>('/automation/run-rules', { apply }),
};
