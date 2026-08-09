# 前后端联调功能清单 & 差距分析

## 一、API 路径映射对比

### 1.1 后端已实现的 API 端点

| 模块 | 方法 | 路径 | 权限 |
|------|------|------|------|
| 认证 | POST | `/api/v1/auth/login` | 公开 |
| 认证 | POST | `/api/v1/auth/register` | 公开 |
| 认证 | GET | `/api/v1/auth/me` | 登录用户 |
| 风险评估 | POST | `/api/v1/risk/analyze` | 登录用户 |
| 风险评估 | GET | `/api/v1/risk/analyze/{request_id}` | 登录用户 |
| 风险评估 | POST | `/api/v1/risk/analyze/batch` | 登录用户 |
| 决策 | POST | `/api/v1/decision/make` | 登录用户 |
| 决策 | GET | `/api/v1/decision/{request_id}` | 登录用户 |
| 决策 | GET | `/api/v1/decision/{request_id}/trace` | 登录用户 |
| 审核 | GET | `/api/v1/review/pending` | 登录用户 |
| 审核 | POST | `/api/v1/review/{request_id}/approve` | 登录用户 |
| 审核 | POST | `/api/v1/review/{request_id}/reject` | 登录用户 |
| 审核 | POST | `/api/v1/review/{request_id}/override` | 登录用户 |
| 规则 | GET | `/api/v1/rules` | 登录用户 |
| 规则 | GET | `/api/v1/rules/tree` | 登录用户 |
| 规则 | POST | `/api/v1/rules` | Admin |
| 规则 | PUT | `/api/v1/rules/{rule_id}` | Admin |
| 规则 | DELETE | `/api/v1/rules/{rule_id}` | Admin |
| 规则 | POST | `/api/v1/rules/{rule_id}/toggle` | Admin |
| 规则 | GET | `/api/v1/rules/{rule_id}/versions` | 登录用户 |
| 规则 | POST | `/api/v1/rules/{rule_id}/rollback` | Admin |
| WebSocket | GET | `/api/v1/ws/alerts` | — |

### 1.2 前端当前调用的 API（与实际后端对比）

| 前端 Service | 方法 | 前端 URL | 对应后端端点 | 匹配状态 |
|-------------|------|---------|------------|---------|
| dashboardService | GET | `/dashboard/summary` | **无** | ❌ 后端缺失 |
| dashboardService | GET | `/dashboard/trends` | **无** | ❌ 后端缺失 |
| dashboardService | GET | `/dashboard/alerts` | **无** | ❌ 后端缺失 |
| dataService | GET | `/raw-data` | **无** | ❌ 后端缺失 |
| dataService | GET | `/raw-data/{id}` | **无** | ❌ 后端缺失 |
| dataService | POST | `/raw-data` | **无** | ❌ 后端缺失 |
| dataService | DELETE | `/raw-data/{id}` | **无** | ❌ 后端缺失 |
| analysisService | GET | `/analysis` | **无** | ❌ 后端缺失 |
| analysisService | GET | `/analysis/{id}` | **无** | ❌ 后端缺失 |
| analysisService | POST | `/analysis/run` | **无** | ❌ 后端缺失 |
| decisionService | GET | `/decisions` | **无** | ❌ 后端缺失 |
| decisionService | GET | `/decisions/{id}` | **无** | ❌ 后端缺失 |
| decisionService | PUT | `/decisions/{id}/approve` | **无** | ❌ 后端缺失 |
| decisionService | PUT | `/decisions/{id}/reject` | **无** | ❌ 后端缺失 |

**结论：前端所有 14 个 API 调用与后端实际端点路径完全不匹配。**

---

## 二、具体差距分析

### 2.1 路径不匹配

| 问题 | 前端路径 | 后端路径 | 修复方向 |
|------|---------|---------|---------|
| 前端 URL 前缀 | `/api` | `/api/v1` | 修改 `api.ts` 中 `baseURL` 为 `/api/v1` |
| 分析模块 | `/analysis` | `/risk/analyze` | 统一路径约定 |
| 决策模块 | `/decisions` | `/decision` | 统一路径约定 |
| 原始数据 | `/raw-data` | 无此模块 | 后端需新增 raw_data 路由 |
| 仪表盘 | `/dashboard` | 无此模块 | 后端需新增 dashboard 路由 |
| 规则模块 | 无 Service | `/rules` | 前端需新增 ruleService |

### 2.2 缺失功能

**后端缺失：**
- 无 Dashboard 统计接口（summary/trends/alerts）
- 无原始数据 CRUD 接口（raw_data 列表/详情/创建/删除）
- 无分析结果列表接口（`/risk/analyze` 只有单条查询）
- 无决策结果列表接口（`/decision` 只有按 request_id 查询）

**前端缺失：**
- 无 authService（登录/注册/获取用户信息）
- 无 ruleService（规则 CRUD/版本管理）
- 无 reviewService（审核操作）
- 登录页面使用模拟数据，未调用真实 API
- 无 WebSocket 连接服务

### 2.3 数据模型不匹配

| 字段 | 前端类型 (models.ts) | 后端 Schema | 差异 |
|------|---------------------|------------|------|
| RawData | `source`, `data_type`, `content` | `source_type`, `source_id`, `payload` | 字段名完全不同 |
| AnalysisResult | `risk_factors`, `confidence`, `agent_log`, `status` | `anomaly_tags`, `analysis_reasoning` | 字段名不同 |
| DecisionResult | `decision_type`, `status`, `reason`, `resolved_at` | `decision`, `explanation`, `reflection_passed` | 字段名和结构不同 |
| RuleNode | `name`, `condition`, `action`, `enabled`, `children` | `rule_name`, `condition_type`, `field_name`, `is_active`, `parent_id` | 结构不同（树 vs 扁平） |
| ApiResponse | `code: number` | `code: string` | 类型不同（`"OK"` vs `200`） |

### 2.4 认证流程不完整

- 前端 `api.ts` 拦截器发送 `Authorization: Bearer <token>`
- 后端 `security.py` 使用 `OAuth2PasswordBearer` 期望 `Authorization: Bearer <token>` → **格式匹配**
- 但前端登录页面是模拟登录，不调用 `/api/v1/auth/login`
- 登录后使用 `mock-token`，无法通过 JWT 验证

---

## 三、修复方案

### 方案 A：后端适配前端（推荐）

后端新增前端需要的接口，同时保留现有 Agent 接口。

**后端新增：**
1. 新增 `app/api/v1/dashboard.py` — Dashboard 统计接口
2. 新增 `app/api/v1/raw_data_crud.py` — 原始数据 CRUD 接口
3. 扩展 `app/api/v1/risk.py` — 新增分析结果列表接口
4. 扩展 `app/api/v1/decision.py` — 新增决策结果列表接口

**前端修改：**
1. 修改 `api.ts` baseURL: `/api` → `/api/v1`
2. 修改各 Service 的 URL 路径与后端对齐
3. 新增 `authService.ts` — 调用真实登录/注册 API
4. 新增 `ruleService.ts` — 规则 CRUD
5. 新增 `reviewService.ts` — 审核操作
6. 修改 `Login.tsx` — 替换模拟登录为真实 API 调用
7. 修改 `models.ts` — 数据模型字段与后端 Schema 对齐
8. 修改 `api.ts` 中 `ApiResponse.code` 类型: `number` → `string`

### 方案 B：前端适配后端

只修改前端，让前端完全适配现有后端接口。

**前端修改：**
1. 修改 `api.ts` baseURL: `/api` → `/api/v1`
2. 重写所有 Service 的 URL 路径，匹配后端实际路径
3. 重写 `models.ts` 数据模型，与后端 Schema 对齐
4. 新增 `authService.ts`、`ruleService.ts`、`reviewService.ts`
5. 修改 `Login.tsx` 调用真实 API
6. 移除 Dashboard 页面中不存在的接口调用（用 mock 数据替代）
7. 移除 RawData 页面中不存在的 CRUD 接口调用

---

## 四、实施步骤（方案 A）

### 步骤 1：后端新增 Dashboard 接口
- 文件：`app/api/v1/dashboard.py`（新建）
- 端点：`GET /api/v1/dashboard/summary`、`GET /api/v1/dashboard/trends`、`GET /api/v1/dashboard/alerts`
- 注册到 `router.py`

### 步骤 2：后端新增原始数据 CRUD 接口
- 文件：`app/api/v1/raw_data_crud.py`（新建）
- 端点：`GET /api/v1/raw-data`、`GET /api/v1/raw-data/{id}`、`POST /api/v1/raw-data`、`DELETE /api/v1/raw-data/{id}`
- 注册到 `router.py`

### 步骤 3：后端扩展分析与决策列表接口
- 修改 `app/api/v1/risk.py`：新增 `GET /api/v1/risk/analyze`（列表）
- 修改 `app/api/v1/decision.py`：新增 `GET /api/v1/decision`（列表）

### 步骤 4：前端统一 API 路径与数据模型
- 修改 `frontend/src/services/api.ts`：baseURL 改为 `/api/v1`
- 修改 `frontend/src/types/models.ts`：字段与后端 Schema 对齐
- 修改 `frontend/src/types/api.ts`：`ApiResponse.code` 改为 `string`
- 修改所有 Service 文件中的 URL 路径

### 步骤 5：前端新增缺失的 Service
- 新建 `frontend/src/services/authService.ts`
- 新建 `frontend/src/services/ruleService.ts`
- 新建 `frontend/src/services/reviewService.ts`

### 步骤 6：前端登录页对接真实 API
- 修改 `frontend/src/pages/Login.tsx`：替换模拟登录为真实 API 调用

### 步骤 7：联调验证
- 启动后端服务
- 启动前端开发服务器
- 逐页面验证 API 调用是否正常

---

## 五、验证清单

| 页面 | 功能 | 验证项 |
|------|------|--------|
| 登录 | 登录 | POST /api/v1/auth/login 返回有效 token |
| 登录 | 注册 | POST /api/v1/auth/register 创建用户 |
| 仪表盘 | 概览 | GET /api/v1/dashboard/summary 返回统计数据 |
| 原始数据 | 列表 | GET /api/v1/raw-data 返回分页数据 |
| 原始数据 | 创建 | POST /api/v1/raw-data 创建数据 |
| 原始数据 | 详情 | GET /api/v1/raw-data/{id} 返回详情 |
| 分析 | 列表 | GET /api/v1/risk/analyze 返回分析列表 |
| 分析 | 运行 | POST /api/v1/risk/analyze 触发分析 |
| 分析 | 详情 | GET /api/v1/risk/analyze/{request_id} 返回结果 |
| 决策 | 列表 | GET /api/v1/decision 返回决策列表 |
| 决策 | 审批 | POST /api/v1/review/{id}/approve |
| 规则 | 列表 | GET /api/v1/rules 返回规则列表 |
| 规则 | 创建 | POST /api/v1/rules 创建规则 |
| 规则 | 版本 | GET /api/v1/rules/{id}/versions |