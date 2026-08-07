import { get } from './api';
import type { DashboardSummary, RiskTrendPoint, AlertItem } from '@/types/models';

export const dashboardService = {
  getSummary: () => get<DashboardSummary>('/dashboard/summary'),
  getTrends: (days?: number) => get<RiskTrendPoint[]>('/dashboard/trends', { days }),
  getAlerts: (limit?: number) => get<AlertItem[]>('/dashboard/alerts', { limit }),
};