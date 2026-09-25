import axios from 'axios';
import type { ApiResponse, PaginatedData } from '@/types/api';
import { useProgressStore } from '@/stores/progressStore';

const api = axios.create({
  withCredentials: true,
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let activeRequests = 0;
let refreshRequest: Promise<unknown> | null = null;

api.interceptors.request.use((config) => {
  // Authentication is cookie-based. Keep this explicit on every request so
  // per-request options or future wrapper changes cannot silently drop it.
  config.withCredentials = true;
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
  async (error) => {
    activeRequests--;
    if (activeRequests <= 0) {
      activeRequests = 0;
      useProgressStore.getState().done();
    }
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/')) {
      if (!error.config?.headers?.['X-Auth-Retry']) {
        try {
          refreshRequest ??= axios.post(`${api.defaults.baseURL}/auth/refresh`, {}, { withCredentials: true }).finally(() => { refreshRequest = null; });
          await refreshRequest;
          error.config.headers['X-Auth-Retry'] = '1';
          return api.request(error.config);
        } catch { /* Expired session: return to login below. */ }
      }
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export async function get<T>(url: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> {
  const response = await api.get<ApiResponse<T>>(url, { params });
  return response.data;
}

/**
 * post 请求。
 * @param timeoutMs 可选超时覆盖：AI 自动化等长耗时接口传更大的值
 *   （本地 Ollama 推理单次可达 15s+，一次自动化含多次 LLM 调用）。
 */
export async function post<T>(url: string, data?: unknown, timeoutMs?: number): Promise<ApiResponse<T>> {
  const response = await api.post<ApiResponse<T>>(url, data, {
    ...(timeoutMs ? { timeout: timeoutMs } : {}),
  });
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

/**
 * 解析分页响应。
 * 后端 PaginatedResponse 结构为扁平的 `{ data: [...], total, page, page_size }`
 * （data 是数组、total 在顶层），本函数同时兼容 `{ data: { items, total } }`
 * 的嵌套结构，统一输出 PaginatedData 形态供列表页使用。
 */
export function extractPaginated<T>(res: ApiResponse<unknown>): PaginatedData<T> {
  const d = res?.data as unknown;
  if (Array.isArray(d)) {
    return {
      items: d as T[],
      total: (res as unknown as { total?: number }).total ?? d.length,
      page: (res as unknown as { page?: number }).page ?? 1,
      page_size: (res as unknown as { page_size?: number }).page_size ?? d.length,
      total_pages: 1,
    };
  }
  if (d && typeof d === 'object' && Array.isArray((d as { items?: unknown }).items)) {
    const nested = d as PaginatedData<T>;
    return {
      items: nested.items,
      total: nested.total ?? nested.items.length,
      page: nested.page ?? 1,
      page_size: nested.page_size ?? nested.items.length,
      total_pages: nested.total_pages ?? 1,
    };
  }
  return { items: [], total: 0, page: 1, page_size: 0, total_pages: 0 };
}

export default api;
