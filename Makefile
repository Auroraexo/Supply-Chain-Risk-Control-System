.PHONY: help install lock sync lint format typecheck security test coverage agent-eval clean docker-build docker-up docker-down db-migrate db-revision

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装 uv
	@echo "安装 uv 包管理器..."
	pip install uv

lock: ## 锁定依赖版本
	uv lock

sync: ## 同步依赖
	uv sync --all-extras

lint: ## 代码检查
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy app/

format: ## 代码格式化
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## 类型检查
	uv run mypy app/

security: ## 安全扫描
	uv run bandit -r app/ -ll
	uv run pip-audit

test: ## 运行单元测试
	uv run pytest tests/unit/ -v --cov=app --cov-report=term-missing

coverage: ## 运行测试并生成覆盖率报告
	uv run pytest tests/unit/ -v --cov=app --cov-report=html
	@echo "覆盖率报告: coverage_html/index.html"

agent-eval: ## 运行 Agent 评估测试
	uv run pytest tests/agent_eval/ -v

integration: ## 运行集成测试
	uv run pytest tests/integration/ -v

test-all: ## 运行所有测试
	uv run pytest tests/ -v --cov=app --cov-report=html

docker-build: ## 构建 Docker 镜像
	docker build -t supply-chain-risk-control:latest .

docker-up: ## 启动 Docker Compose
	docker compose up -d

docker-down: ## 停止 Docker Compose
	docker compose down

docker-logs: ## 查看 Docker 日志
	docker compose logs -f app

db-revision: ## 创建数据库迁移文件 (用法: make db-revision MSG="描述")
	uv run alembic revision --autogenerate -m "$(MSG)"

db-migrate: ## 运行数据库迁移
	uv run alembic upgrade head

db-downgrade: ## 回滚数据库迁移
	uv run alembic downgrade -1

db-reset: ## 重置数据库（危险操作）
	uv run alembic downgrade base
	uv run alembic upgrade head

run: ## 启动开发服务器
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## 启动生产服务器
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

pre-commit-install: ## 安装 pre-commit hooks
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

pre-commit-run: ## 手动运行 pre-commit
	uv run pre-commit run --all-files

clean: ## 清理临时文件
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf coverage_html/ .coverage .mypy_cache/ 2>/dev/null || true
	@echo "清理完成"