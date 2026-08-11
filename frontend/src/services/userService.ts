import { get, post, put, del } from './api';
import type { User } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export interface UserQueryParams extends PaginationParams {
  role?: string;
  search?: string;
}

export const userService = {
  list: (params?: UserQueryParams) => get<PaginatedData<User>>('/users', params as Record<string, unknown>),
  create: (data: { username: string; email: string; password: string; role: string }) =>
    post<User>('/users', data),
  update: (userId: string, data: { email?: string; role?: string; is_active?: boolean }) =>
    put<User>(`/users/${userId}`, data),
  delete: (userId: string) => del<void>(`/users/${userId}`),
};
