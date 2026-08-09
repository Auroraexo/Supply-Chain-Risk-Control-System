import { get, post } from './api';
import type { User } from '@/types/models';
import type { LoginRequest, LoginResponse } from '@/types/api';

export const authService = {
  login: (data: LoginRequest) => post<LoginResponse>('/auth/login', data),
  register: (data: { username: string; email: string; password: string; role?: string }) =>
    post<User>('/auth/register', data),
  getMe: () => get<User>('/auth/me'),
};