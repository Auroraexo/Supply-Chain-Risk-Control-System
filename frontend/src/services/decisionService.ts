import { get, post } from './api';
import type { DecisionResult } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export const decisionService = {
  list: (params?: PaginationParams) => get<PaginatedData<DecisionResult>>('/decision', params as Record<string, unknown>),
  getById: (requestId: string) => get<DecisionResult>(`/decision/${requestId}`),
  approve: (requestId: string, comment?: string) => post<DecisionResult>(`/review/${requestId}/approve`, { comment }),
  reject: (requestId: string, comment: string) => post<DecisionResult>(`/review/${requestId}/reject`, { comment }),
};