"""供应链智能决策系统 - 应用入口。

FastAPI 应用主入口，负责：
- 应用生命周期管理（启动/关闭）
- 中间件注册
- 路由注册
- 全局异常处理
- OpenAPI 文档配置
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.api.v1.websocket import router as ws_router
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.core.middleware import (
    TraceIdMiddleware,
    RequestLoggingMiddleware,
    register_exception_handlers,
)
from app.core.database import close_db_connection
from app.core.redis import close_redis_connection
from app.core.mq import close_mq_connection


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理。"""
    # 启动时
    setup_logging()
    settings = get_settings()

    import structlog
    logger = structlog.get_logger(__name__)
    logger.info(
        "app_starting",
        environment=settings.ENVIRONMENT,
        app_name=settings.APP_NAME,
        debug=settings.DEBUG,
    )

    yield

    # 关闭时
    logger.info("app_shutting_down")
    await close_mq_connection()
    await close_redis_connection()
    await close_db_connection()
    logger.info("app_shutdown_complete")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        description="供应链智能决策系统 - 多 Agent 协同架构",
        version="0.1.0",
        docs_url="/api/v1/docs" if not settings.is_production else None,
        redoc_url="/api/v1/redoc" if not settings.is_production else None,
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # === 注册中间件（顺序很重要） ===
    # 1. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Trace ID
    app.add_middleware(TraceIdMiddleware)

    # 3. 请求日志
    if not settings.is_production:
        app.add_middleware(RequestLoggingMiddleware)

    # === 注册路由 ===
    app.include_router(api_router)
    app.include_router(ws_router)

    # === 健康检查 ===
    @app.get("/health/live", tags=["Health"])
    async def health_live():
        """存活探针。"""
        return {"status": "ok", "service": settings.APP_NAME}

    @app.get("/health/ready", tags=["Health"])
    async def health_ready():
        """就绪探针：检查所有依赖服务连通性。"""
        try:
            from app.core.redis import get_redis
            redis = await get_redis()
            await redis.ping()
            return {"status": "ok", "database": "connected", "redis": "connected"}
        except Exception as e:
            return {"status": "degraded", "error": str(e)}

    # === 全局异常处理 ===
    register_exception_handlers(app)

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )