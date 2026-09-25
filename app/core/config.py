"""应用配置管理模块。

使用 pydantic-settings 从环境变量 / .env 文件加载配置。
支持多环境：development / test / staging / production。
"""

from functools import lru_cache
from contextvars import ContextVar
from typing import Any, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from sqlalchemy.engine import make_url
from urllib.parse import urlparse


class Settings(BaseSettings):
    """全局应用配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    # === 应用配置 ===
    ENVIRONMENT: str = "development"
    APP_NAME: str = "supply-chain-risk-control"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # === 服务端口 ===
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # === 数据库 ===
    DATABASE_URL: str = "mysql+asyncmy://root:password@localhost:3306/supply_chain_risk"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE: int = 3600

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # === JWT 认证 ===
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SETTINGS_ENCRYPTION_KEY: str = ""

    # === RabbitMQ ===
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # === CORS ===
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"

    # === LLM ===
    LLM_PROVIDER: str = "openai"  # openai / anthropic / azure_openai / local
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: Optional[str] = None
    LLM_API_VERSION: str = "2024-10-21"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4000
    LLM_TIMEOUT: int = 30
    LLM_MOCK_MODE: bool = False

    # === Ollama ===
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # === Model Selector（智能模型选择）===
    MODEL_SELECTOR_ENABLED: bool = True
    MODEL_SELECTOR_SMALL_THRESHOLD: float = 8.0
    MODEL_SELECTOR_COMPLEXITY_THRESHOLD: float = 0.5
    MODEL_SELECTOR_CACHE_TTL: int = 300
    MODEL_SELECTOR_PREFERRED_SMALL: str = ""
    MODEL_SELECTOR_PREFERRED_LARGE: str = ""

    # === LangSmith ===
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "supply-chain-risk"

    # === 安全 ===
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1)
    LOGIN_RATE_LIMIT_PER_MINUTE: int = Field(default=10, ge=1)
    REQUEST_BODY_MAX_SIZE_MB: int = Field(default=10, ge=1)

    @model_validator(mode="after")
    def validate_production(self):
        if self.is_production:
            if len(self.JWT_SECRET_KEY) < 32 or self.JWT_SECRET_KEY.startswith("change-me"):
                raise ValueError("生产环境必须配置至少 32 字符的随机 JWT_SECRET_KEY")
            if self.DEBUG:
                raise ValueError("生产环境禁止 DEBUG=true")
            db_url = make_url(self.DATABASE_URL)
            if db_url.username == "root" or not db_url.password or db_url.password == "password":
                raise ValueError("生产数据库必须使用独立低权限账号和非默认密码")
            mq_url = urlparse(self.RABBITMQ_URL)
            if mq_url.username == "guest" or not mq_url.password or mq_url.password == "guest":
                raise ValueError("生产 RabbitMQ 必须使用独立账号和非默认密码")
            from cryptography.fernet import Fernet

            try:
                Fernet(self.SETTINGS_ENCRYPTION_KEY.encode())
            except (ValueError, TypeError) as exc:
                raise ValueError("生产环境必须配置有效的 SETTINGS_ENCRYPTION_KEY") from exc
        return self

    # === 通知 ===
    WECOM_WEBHOOK_URL: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例。"""
    return Settings()


# CLI-only overrides remain available for tests. API requests use an isolated
# ContextVar loaded from the encrypted database on each request/worker instance.
_runtime_llm_config: dict[str, Any] = {}
request_llm_config: ContextVar[dict[str, Any] | None] = ContextVar(
    "request_llm_config", default=None
)


def get_effective_llm_config() -> dict[str, Any]:
    """Return environment defaults merged with the latest UI configuration."""
    settings = get_settings()
    config: dict[str, Any] = {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "api_key": settings.LLM_API_KEY,
        "base_url": settings.LLM_BASE_URL or "",
        "api_version": settings.LLM_API_VERSION,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "mock_mode": settings.LLM_MOCK_MODE,
        "smart_routing": settings.MODEL_SELECTOR_ENABLED,
    }
    config.update({key: value for key, value in _runtime_llm_config.items() if value is not None})
    config.update(request_llm_config.get() or {})
    return config


def set_runtime_llm_config(config: dict[str, Any]) -> None:
    """Apply a validated UI configuration to the current process."""
    _runtime_llm_config.clear()
    _runtime_llm_config.update(config)
