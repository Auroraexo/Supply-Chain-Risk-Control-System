import { get, put, post } from './api';
import type { LLMConfig } from '@/types/models';

export interface NotificationChannel {
  id: string;
  type: string;
  name: string;
  enabled: boolean;
  config: string;
}

export interface NotificationSettings {
  channels: NotificationChannel[];
}

interface LLMTestResult {
  success: boolean;
  message: string;
  latency_ms: number | null;
}

export interface OllamaModelInfo {
  name: string;
  size: string;
  parameter_count: string;
  modified_at: string;
}

export interface OllamaModelListResult {
  models: OllamaModelInfo[];
  available: boolean;
  message: string;
}

interface LLMTestConfig {
  provider: string;
  model: string;
  api_key: string;
  base_url: string;
  api_version: string;
  ollama_base_url: string;
}

export const settingsService = {
  getLLMConfig: () => get<LLMConfig>('/settings/llm'),
  updateLLMConfig: (config: Partial<LLMConfig>) => put<LLMConfig>('/settings/llm', config),
  testLLMConnection: (config: LLMTestConfig) =>
    post<LLMTestResult>('/settings/llm/test', config),
  listOllamaModels: (baseUrl: string = 'http://localhost:11434') =>
    get<OllamaModelListResult>(`/settings/llm/ollama-models?base_url=${encodeURIComponent(baseUrl)}`),
  getNotificationSettings: () => get<NotificationSettings>('/settings/notifications'),
  updateNotificationSettings: (settings: NotificationSettings) =>
    put<NotificationSettings>('/settings/notifications', settings),
};
