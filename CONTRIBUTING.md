# Contributing to Supply Chain Risk Control System

感谢你愿意为本项目贡献代码！本文件说明如何搭建开发环境、提交 PR，以及代码规范。

## 行为准则

请以尊重、专业的方式参与讨论。不欢迎人身攻击、歧视性言论或无意义的争论。

## 开发环境

### 前置依赖

- Python ≥ 3.12
- Node.js ≥ 18
- Docker & Docker Compose（推荐，一键起 MySQL / Redis / RabbitMQ）

### 后端

```bash
# 克隆并进入目录
git clone git@github.com:Auroraexo/Supply-Chain-Risk-Control-System.git
cd Supply-Chain-Risk-Control-System

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # macOS / Linux

# 安装依赖（含开发工具）
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env：至少填 DATABASE_URL / REDIS_URL / RABBITMQ_URL / JWT_SECRET_KEY

# 启动中间件（如果不用 Docker）
# 自行启动 MySQL 8 / Redis 7 / RabbitMQ 3.x

# 执行数据库迁移
alembic upgrade head

# 启动后端
python -m app.main
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### 一键 Docker（最省事）

```bash
cp .env.example .env
# 编辑 .env 设置强密码
docker compose up -d --build
```

## 代码规范

提交 PR 前请确保以下命令全部通过：

```bash
# 代码格式化
ruff format .

# 静态检查
ruff check .

# 类型检查
mypy app/

# 安全扫描
bandit -r app/ -c pyproject.toml

# 测试（含覆盖率 ≥ 80%）
pytest --cov=app --cov-report=term
```

项目已配置 `pre-commit`，建议安装：

```bash
pre-commit install
```

## 分支与提交

- 主分支：`main`，始终保持可发布状态。
- 功能分支命名：`feat/xxx`、`fix/xxx`、`docs/xxx`、`refactor/xxx`。
- 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：
  - `feat: 新增规则树可视化编辑`
  - `fix: 修复 Outbox 重复投递`
  - `docs: 补充部署说明`
  - `refactor: 抽取 Agent 路由函数`
  - `test: 增加 Reflection 节点用例`

## Pull Request 流程

1. Fork 本仓库，从 `main` 切出特性分支。
2. 完成代码 + 补充测试 + 更新相关文档。
3. 本地跑通 `ruff / mypy / bandit / pytest`。
4. 推送分支并开启 PR，描述里说明：
   - 解决了什么问题 / 为什么要做
   - 关键设计取舍
   - 测试方式与覆盖到的场景
   - 是否有 Breaking Change
5. 通过 CI 并至少一人 review 后合并。

## 目录约定

- 新增 API：放到 `app/api/v1/`，并在 README「API 概览」补一行。
- 新增 Agent 节点：放到 `app/agents/nodes/`，并在 `app/agents/graphs/decision_graph.py` 注册节点与路由。
- 新增数据模型：放到 `app/models/`，并生成 alembic 迁移脚本。
- 新增业务逻辑：放到 `app/services/`，不要把逻辑写在 API 路由里。
- 新增前端页面：放到 `frontend/src/pages/`。

## 报告 Issue

提交 Issue 时请包含：

- 环境：操作系统、Python 版本、Docker / 本地
- 复现步骤
- 预期行为 vs 实际行为
- 相关日志（注意脱敏，不要贴 API Key）

## License

提交 PR 即代表你同意将贡献以 [MIT License](LICENSE) 授权给本项目。
