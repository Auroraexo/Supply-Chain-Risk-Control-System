"""结构化日志配置模块。

使用 structlog 实现结构化日志，支持 JSON 输出。
集成 OpenTelemetry trace_id 自动注入。
"""

import logging

import structlog

from app.core.config import get_settings


def setup_logging() -> None:
    """初始化结构化日志配置。

    在应用启动时调用一次。
    开发环境输出彩色控制台日志，生产环境输出 JSON 格式。
    """
    settings = get_settings()

    # 共享的时间戳处理器
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    # 共享的预处理器链
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    if settings.is_production:
        # 生产环境：JSON 日志输出
        renderer = structlog.processors.JSONRenderer()
    else:
        # 开发环境：彩色控制台输出
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # 配置 structlog
    structlog.configure(
        processors=shared_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 配置标准库日志格式
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors[:4],
        processor=renderer,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # 降低第三方库日志级别
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取结构化日志记录器。"""
    return structlog.get_logger(name or __name__)