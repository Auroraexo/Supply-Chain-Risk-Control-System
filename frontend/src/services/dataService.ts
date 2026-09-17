import { get, post, del, extractPaginated } from './api';
import type { RawData } from '@/types/models';
import type { PaginatedData, RawDataQueryParams } from '@/types/api';

export const dataService = {
  list: async (params?: RawDataQueryParams): Promise<PaginatedData<RawData>> => {
    const res = await get<unknown>('/raw-data', params as Record<string, unknown>);
    return extractPaginated<RawData>(res);
  },
  getById: (id: string) => get<RawData>(`/raw-data/${id}`),
  create: (data: Partial<RawData>) => post<RawData>('/raw-data', data),
  delete: (id: string) => del<void>(`/raw-data/${id}`),
};
