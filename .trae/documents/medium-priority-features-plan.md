# 中优先级功能完善 — 实现计划

## 上下文

基于系统全面测试和开发清单，当前需完成 12 项中优先级功能。其中 4 项已有基础实现（#6 数据录入弹窗、#10 决策审批、#15 告警时间线、#16 LLM配置、#17 通知设置），实际需新增/增强 8 项。

## 前置依赖安装

```bash
cd frontend
npm install recharts @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

## 实施步骤

### 步骤 1：#7 数据详情侧边抽屉 (Drawer)

**新建文件**：
- `frontend/src/components/ui/Drawer.tsx` — 右侧滑入抽屉组件

**修改文件**：
- `frontend/src/pages/RawData/RawDataList.tsx` — 行点击改为打开抽屉，保留"查看详情"按钮跳转全屏页

**关键细节**：
- Drawer 组件模式参照 Modal 组件：open/onClose props + 动画 + ESC 关闭
- 抽屉内容复用 RawDataDetail 的基本信息+JSON内容展示
- 宽度 w-96 或 max-w-md，从右侧滑入

### 步骤 2：#8 风险分析卡片+表格混合布局

**修改文件**：
- `frontend/src/pages/Analysis/AnalysisList.tsx`

**关键细节**：
- 添加 viewMode state (`'list' | 'card'`)，默认 `'list'`
- 工具栏添加视图切换按钮（LayoutGrid/List 图标）
- 卡片视图：2列 Grid 布局，每个 Card 显示风险等级徽章、评分进度条、异常标签列表
- 保持现有列表视图不变

### 步骤 3：#9 风险详情全屏页增强

**修改文件**：
- `frontend/src/pages/Analysis/AnalysisDetail.tsx`
- `frontend/src/types/models.ts` — 添加 AgentExecutionLog 类型

**新建文件**：
- `frontend/src/services/agentLogService.ts` — 调用 GET /decision/{id}/trace

**关键细节**：
- 添加 Agent 执行日志区域（调用决策追踪 API）
- 决策路径可视化：step-by-step 时间线展示
- 风险因子详情卡片（从 facts_summary 提取展示）

### 步骤 4：#11 规则树拖拽排序

**修改文件**：
- `frontend/src/pages/Rules/RuleEditor.tsx`

**关键细节**：
- 使用 @dnd-kit/core 的 DndContext + SortableContext
- 为 RuleNodeItem 添加拖拽手柄（GripVertical 图标）
- 拖拽仅在同级节点间排序
- 拖拽结束后调用 ruleService.update 更新优先级
- 保留现有展开/折叠、编辑、删除功能

### 步骤 5：#12 规则版本对比视图

**新建文件**：
- `frontend/src/components/ui/DiffView.tsx` — 并排对比组件

**修改文件**：
- `frontend/src/pages/Rules/RuleVersions.tsx`

**关键细节**：
- 添加两个版本选择器（下拉选择）
- DiffView 组件：左右两列显示 snapshot，差异字段高亮（bg-risk-low/10 绿色背景）
- 对比字段：rule_name, rule_type, field_name, operator, threshold_value, weight, priority, logic_op

### 步骤 6：#13 规则测试功能

**修改文件**：
- `frontend/src/pages/Rules/RuleEditor.tsx`

**关键细节**：
- 在工具栏添加"测试规则"按钮
- Modal 弹窗：左侧输入测试 JSON 数据，右侧显示执行结果
- 调用后端 POST /rules/test（需后端新增端点，或在前端模拟规则匹配逻辑）
- 显示：匹配结果（是/否）、匹配的规则路径、评分

### 步骤 7：#14 风险趋势图（Recharts）

**修改文件**：
- `frontend/src/pages/Dashboard.tsx`

**关键细节**：
- 安装 recharts 后替换 TrendChart 组件
- 使用 Recharts AreaChart：4 条面积图（critical/high/medium/low 各一条）
- 保留图例、tooltip、响应式容器
- 使用现有颜色：critical=#EF4444, high=#F97316, medium=#F59E0B, low=#10B981

### 步骤 8：#16-17 系统设置后端 API 连接

**新建文件**：
- `app/api/v1/settings.py` — 设置 API 端点
- `app/schemas/settings.py` — 设置 Schema
- `frontend/src/services/settingsService.ts` — 前端设置服务

**修改文件**：
- `app/api/v1/router.py` — 注册 settings 路由
- `frontend/src/pages/Settings/Settings.tsx` — LLMConfig 和 NotificationSettings 连接真实 API

**后端 API 端点**：
- `GET /api/v1/settings/llm` — 获取 LLM 配置
- `PUT /api/v1/settings/llm` — 更新 LLM 配置
- `POST /api/v1/settings/llm/test` — 测试 LLM 连接
- `GET /api/v1/settings/notifications` — 获取通知渠道配置
- `PUT /api/v1/settings/notifications` — 更新通知渠道配置

**关键细节**：
- LLM 配置存储到数据库或配置文件（settings 表）
- 测试连接功能：调用 LLM API 发送简单请求验证
- 通知渠道配置：email/webhook/slack 的启用/禁用和 URL 配置

## 实施顺序

1. `npm install` 安装依赖（并行）
2. #7 Drawer 组件（独立，无依赖）
3. #8 分析卡片布局（独立）
4. #9 分析详情增强（独立）
5. #16-17 后端 settings API（为前端提供数据源）
6. #16-17 前端 settings 连接（依赖后端 API）
7. #11 规则树拖拽（依赖 @dnd-kit）
8. #12 版本对比（独立）
9. #13 规则测试（依赖规则树）
10. #14 Recharts 趋势图（依赖 recharts）

## 验证方式

1. 启动后端 `python -m uvicorn app.main:app --port 8000`
2. 启动前端 `cd frontend && npm run dev`
3. 逐项验证：
   - 原始数据：点击行 → 抽屉弹出，可关闭
   - 风险分析：切换卡片/列表视图，卡片正常渲染
   - 风险详情：Agent 日志时间线展示
   - 规则树：拖拽节点排序，刷新后顺序保持
   - 版本对比：选择两个版本，差异高亮显示
   - 规则测试：输入 JSON → 显示匹配结果
   - 仪表盘：Recharts 面积图渲染，tooltip 正常
   - 设置：LLM 配置保存/加载，测试连接按钮