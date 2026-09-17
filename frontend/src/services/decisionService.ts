import { get, post, extractPaginated } from './api';
import type { DecisionResult } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export const decisionService = {
  list: async (params?: PaginationParams): Promise<PaginatedData<DecisionResult>> => {
    const res = await get<unknown>('/decision', params as Record<string, unknown>);
    return extractPaginated<DecisionResult>(res);
  },
  getById: (requestId: string) => get<DecisionResult>(`/decision/${requestId}`),
  approve: (requestId: string, comment?: string) => post<DecisionResult>(`/review/${requestId}/approve`, { action: 'approve', comment }),
  reject: (requestId: string, comment: string) => post<DecisionResult>(`/review/${requestId}/reject`, { action: 'reject', comment }),
  escalate: (requestId: string, comment: string) => post<DecisionResult>(`/review/${requestId}/override`, { action: 'override', comment, override_decision: 'escalate' }),
};
