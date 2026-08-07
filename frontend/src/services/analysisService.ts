import { get, post } from './api';
import type { AnalysisResult } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export const analysisService = {
  list: (params?: PaginationParams) => get<PaginatedData<AnalysisResult>>('/analysis', params as Record<string, unknown>),
  getById: (id: string) => get<AnalysisResult>(`/analysis/${id}`),
  run: (rawDataId: string) => post<AnalysisResult>('/analysis/run', { raw_data_id: rawDataId }),
};