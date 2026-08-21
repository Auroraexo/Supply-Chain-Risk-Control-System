import axios from 'axios';
import type { ApiResponse } from '@/types/api';
import { useProgressStore } from '@/stores/progressStore';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let activeRequests = 0;

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  activeRequests++;
  if (activeRequests === 1) {
    useProgressStore.getState().start();
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    activeRequests--;
    if (activeRequests <= 0) {
      activeRequests = 0;
      useProgressStore.getState().done();
    }
    return response;
  },
  (error) => {
    activeRequests--;
    if (activeRequests <= 0) {
      activeRequests = 0;
      useProgressStore.getState().done();
    }
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export async function get<T>(url: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> {
  const response = await api.get<ApiResponse<T>>(url, { params });
  return response.data;
}

export async function post<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const response = await api.post<ApiResponse<T>>(url, data);
  return response.data;
}

export async function put<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const response = await api.put<ApiResponse<T>>(url, data);
  return response.data;
}

export async function del<T>(url: string): Promise<ApiResponse<T>> {
  const response = await api.delete<ApiResponse<T>>(url);
  return response.data;
}

export default api;