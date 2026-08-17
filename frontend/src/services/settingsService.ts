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

export const settingsService = {
  getLLMConfig: () => get<LLMConfig>('/settings/llm'),
  updateLLMConfig: (config: Partial<LLMConfig>) => put<LLMConfig>('/settings/llm', config),
  testLLMConnection: (config: { provider: string; model: string; api_key: string }) =>
    post<LLMTestResult>('/settings/llm/test', config),
  getNotificationSettings: () => get<NotificationSettings>('/settings/notifications'),
  updateNotificationSettings: (settings: NotificationSettings) =>
    put<NotificationSettings>('/settings/notifications', settings),
};