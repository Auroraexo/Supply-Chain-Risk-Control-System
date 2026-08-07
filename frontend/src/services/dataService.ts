import { get, post, del } from './api';
import type { RawData } from '@/types/models';
import type { PaginatedData, RawDataQueryParams } from '@/types/api';

export const dataService = {
  list: (params?: RawDataQueryParams) => get<PaginatedData<RawData>>('/raw-data', params as Record<string, unknown>),
  getById: (id: string) => get<RawData>(`/raw-data/${id}`),
  create: (data: Partial<RawData>) => post<RawData>('/raw-data', data),
  delete: (id: string) => del<void>(`/raw-data/${id}`),
};