import { get, post } from './api';
import type { AnalysisResult } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export const analysisService = {
  list: (params?: PaginationParams) => get<PaginatedData<AnalysisResult>>('/risk/analyze', params as Record<string, unknown>),
  getById: (requestId: string) => get<AnalysisResult>(`/risk/analyze/${requestId}`),
  run: (rawDataId: string) => post<AnalysisResult>('/risk/analyze', { raw_data_id: rawDataId }),
};