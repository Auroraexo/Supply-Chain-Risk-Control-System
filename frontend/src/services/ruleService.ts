import { get, post, put, del, extractPaginated } from './api';
import type { RuleNode, RuleVersion } from '@/types/models';
import type { PaginatedData, PaginationParams } from '@/types/api';

export const ruleService = {
  list: async (params?: PaginationParams): Promise<PaginatedData<RuleNode>> => {
    const res = await get<unknown>('/rules', params as Record<string, unknown>);
    return extractPaginated<RuleNode>(res);
  },
  getTree: () => get<RuleNode[]>('/rules/tree'),
  create: (data: Partial<RuleNode>) => post<RuleNode>('/rules', data),
  test: (context: Record<string, unknown>) =>
    post<{ matched: boolean; path: string[]; score: number; details: Array<{ rule_name: string; matched: boolean; actual: unknown }> }>('/rules/test', { context }),
  update: (ruleId: string, data: Partial<RuleNode>) => put<RuleNode>(`/rules/${ruleId}`, data),
  delete: (ruleId: string) => del<void>(`/rules/${ruleId}`),
  toggle: (ruleId: string, isActive: boolean) => post<RuleNode>(`/rules/${ruleId}/toggle`, { is_active: isActive }),
  getVersions: (ruleId: string) => get<RuleVersion[]>(`/rules/${ruleId}/versions`),
  rollback: (ruleId: string, version: number) => post<RuleNode>(`/rules/${ruleId}/rollback?version=${version}`, null),
};