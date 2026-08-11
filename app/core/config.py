"""应用配置管理模块。

使用 pydantic-settings 从环境变量 / .env 文件加载配置。
支持多环境：development / test / staging / production。
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局应用配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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

    # === RabbitMQ ===
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # === CORS ===
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"

    # === LLM ===
    LLM_PROVIDER: str = "openai"  # openai / anthropic / azure_openai / local
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: Optional[str] = None
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
    RATE_LIMIT_PER_MINUTE: int = 60
    REQUEST_BODY_MAX_SIZE_MB: int = 10

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