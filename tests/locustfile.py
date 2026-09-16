"""Locust 性能压测脚本。

压测关键 API（蓝图目标：QPS > 100）。

使用方法：
    # 启动 Web UI（http://localhost:8089）
    uv run locust -f tests/locustfile.py --host=http://localhost:8000

    # 无头模式压测（1 分钟，50 并发用户）
    uv run locust -f tests/locustfile.py --host=http://localhost:8000 \
        --headless -u 50 -r 5 -t 1m --html locust_report.html

环境变量：
    LOCUST_USERNAME / LOCUST_PASSWORD — 登录凭据（默认 admin/admin123），
    登录失败时自动降级为匿名压测（仅压测公开端点）。
"""

import os

from locust import HttpUser, between, task

_USERNAME = os.getenv("LOCUST_USERNAME", "admin")
_PASSWORD = os.getenv("LOCUST_PASSWORD", "admin123")


class SupplyChainUser(HttpUser):
    """模拟前端用户行为：登录 → 浏览规则/仪表盘 → 查询原始数据。"""

    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        """任务开始时登录一次，失败则保持匿名。"""
        self.token = None
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": _USERNAME, "password": _PASSWORD},
            name="/api/v1/auth/login [setup]",
        )
        if resp.status_code == 200:
            data = resp.json().get("data") or {}
            self.token = data.get("access_token")
            self.client.headers["Authorization"] = f"Bearer {self.token}"

    @task(3)
    def list_rules(self) -> None:
        """规则列表 — 高频只读查询。"""
        self.client.get("/api/v1/rules")

    @task(3)
    def dashboard_summary(self) -> None:
        """仪表盘统计 — 首页聚合查询。"""
        self.client.get("/api/v1/dashboard/summary")

    @task(2)
    def list_raw_data(self) -> None:
        """原始数据分页列表。"""
        self.client.get("/api/v1/raw-data?page=1&page_size=20")

    @task(1)
    def health_live(self) -> None:
        """存活探针 — 基线延迟参考。"""
        self.client.get("/health/live")
