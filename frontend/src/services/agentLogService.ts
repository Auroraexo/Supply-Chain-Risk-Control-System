import { get } from './api';
import type { DecisionTrace } from '@/types/models';

export const agentLogService = {
  getDecisionTrace: (requestId: string) => get<DecisionTrace>(`/decision/${requestId}/trace`),
};