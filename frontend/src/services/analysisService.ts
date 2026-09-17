import { get, post, extractPaginated } from './api';
import type { AnalysisResult } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export const analysisService = {
  list: async (params?: PaginationParams): Promise<PaginatedData<AnalysisResult>> => {
    const res = await get<unknown>('/risk/analyze', params as Record<string, unknown>);
    return extractPaginated<AnalysisResult>(res);
  },
  getById: (requestId: string) => get<AnalysisResult>(`/risk/analyze/${requestId}`),
  run: (rawDataId: string, forceReanalyze = false) =>
    post<AnalysisResult>('/risk/analyze', { raw_data_id: rawDataId, force_reanalyze: forceReanalyze }),
};
