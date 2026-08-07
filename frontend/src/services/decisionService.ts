import { get, put } from './api';
import type { DecisionResult } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export const decisionService = {
  list: (params?: PaginationParams) => get<PaginatedData<DecisionResult>>('/decisions', params as Record<string, unknown>),
  getById: (id: string) => get<DecisionResult>(`/decisions/${id}`),
  approve: (id: string, reason?: string) => put<DecisionResult>(`/decisions/${id}/approve`, { reason }),
  reject: (id: string, reason: string) => put<DecisionResult>(`/decisions/${id}/reject`, { reason }),
};