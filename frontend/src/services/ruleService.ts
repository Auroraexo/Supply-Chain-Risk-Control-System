import { get, post, put, del } from './api';
import type { RuleNode, RuleVersion } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export const ruleService = {
  list: (params?: PaginationParams) => get<PaginatedData<RuleNode>>('/rules', params as Record<string, unknown>),
  getTree: () => get<RuleNode[]>('/rules/tree'),
  create: (data: Partial<RuleNode>) => post<RuleNode>('/rules', data),
  update: (ruleId: string, data: Partial<RuleNode>) => put<RuleNode>(`/rules/${ruleId}`, data),
  delete: (ruleId: string) => del<void>(`/rules/${ruleId}`),
  toggle: (ruleId: string, isActive: boolean) => post<RuleNode>(`/rules/${ruleId}/toggle`, { is_active: isActive }),
  getVersions: (ruleId: string) => get<RuleVersion[]>(`/rules/${ruleId}/versions`),
  rollback: (ruleId: string, version: number) => post<RuleNode>(`/rules/${ruleId}/rollback`, null, { version }),
};