"""自定义中间件模块。

包含:
- TraceIdMiddleware: 自动注入 trace_id 到请求上下文
- RequestLoggingMiddleware: 请求日志记录
- MetricsMiddleware: Prometheus 指标采集
- ExceptionHandlerMiddleware: 全局异常处理
"""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import AppException
from app.core.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL

# 指标路径本身不记录，避免自增噪音
_METRICS_PATH = "/metrics"

logger = structlog.get_logger(__name__)


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Trace ID 中间件。

    自动为每个请求生成或继承 trace_id。
    注入到 structlog 上下文和响应头中。
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 从请求头获取或生成 trace_id
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        request.state.trace_id = trace_id

        # 注入到 structlog 上下文
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        try:
            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            return response
        finally:
            structlog.contextvars.unbind_contextvars("trace_id")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件。

    记录每个请求的方法、路径、状态码和耗时。
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.monotonic()

        response = await call_next(request)

        elapsed_ms = round((time.monotonic() - start_time) * 1000, 2)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            client_ip=request.client.host if request.client else None,
        )

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Prometheus 指标中间件。

    记录每个请求的 QPS（http_requests_total）与延迟分布
    （http_request_duration_seconds）。
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path == _METRICS_PATH:
            return await call_next(request)

        method = request.method
        # 使用路由模板而非实际路径，避免高基数（如 /api/v1/raw-data/{id}）

        start_time = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start_time
        # Routing is resolved by call_next, not before it. Collapse unknown paths.
        route = request.scope.get("route")
        path_template = getattr(route, "path", "unmatched")

        HTTP_REQUESTS_TOTAL.labels(
            method=method, path=path_template, status=response.status_code
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path_template).observe(elapsed)

        return response


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """处理自定义应用异常。"""
        trace_id = getattr(request.state, "trace_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code.value,
                "message": exc.message,
                "detail": exc.detail,
                "trace_id": trace_id,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """处理未捕获的通用异常。"""
        trace_id = getattr(request.state, "trace_id", None)
        logger.exception("unhandled_exception", error=str(exc), trace_id=trace_id)
        return JSONResponse(
            status_code=500,
            content={
                "code": "ERR_UNKNOWN",
                "message": "服务器内部错误",
                "detail": {"error": str(exc)} if not get_settings().is_production else {},
                "trace_id": trace_id,
            },
        )


# 延迟导入避免循环依赖
from app.core.config import get_settings
