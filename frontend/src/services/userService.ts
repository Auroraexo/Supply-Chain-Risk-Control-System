import { get, post, put, del, extractPaginated } from './api';
import type { User } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export interface UserQueryParams extends PaginationParams {
  role?: string;
  search?: string;
}

export const userService = {
  list: async (params?: UserQueryParams): Promise<PaginatedData<User>> => {
    const res = await get<unknown>('/users', params as Record<string, unknown>);
    return extractPaginated<User>(res);
  },
  create: (data: { username: string; email: string; password: string; role: string }) =>
    post<User>('/users', data),
  update: (userId: string, data: { email?: string; role?: string; is_active?: boolean }) =>
    put<User>(`/users/${userId}`, data),
  delete: (userId: string) => del<void>(`/users/${userId}`),
};
