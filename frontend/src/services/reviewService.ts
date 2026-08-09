import { get, post } from './api';
import type { DecisionResult } from '@/types/models';
import type { PaginatedData } from '@/types/api';

export const reviewService = {
  getPending: (page?: number, pageSize?: number) =>
    get<PaginatedData<DecisionResult>>('/review/pending', { page, page_size: pageSize }),
  approve: (requestId: string, comment?: string) =>
    post<DecisionResult>(`/review/${requestId}/approve`, { comment }),
  reject: (requestId: string, comment: string) =>
    post<DecisionResult>(`/review/${requestId}/reject`, { comment }),
  override: (requestId: string, comment: string, overrideDecision: string) =>
    post<DecisionResult>(`/review/${requestId}/override`, { comment, override_decision: overrideDecision }),
};