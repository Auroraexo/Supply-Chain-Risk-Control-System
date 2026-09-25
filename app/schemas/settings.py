"""设置相关 Pydantic 模型。"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal
from urllib.parse import urlparse

Provider = Literal["openai", "anthropic", "azure_openai", "local"]


class LLMConfigRequest(BaseModel):
    """LLM 配置请求。"""

    provider: Provider = Field(default="openai", description="LLM提供商")
    model: str = Field(default="gpt-4o-mini", min_length=1, max_length=200, description="模型名称")
    api_key: str = Field(default="", description="API密钥")
    base_url: str = Field(default="", description="Provider API 基础地址")
    api_version: str = Field(default="2024-10-21", description="Azure OpenAI API 版本")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama 服务地址")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=4096, ge=1, le=128000, description="最大Token数")
    mock_mode: bool = Field(default=False, description="Mock模式")
    smart_routing: bool = Field(default=False, description="智能路由")
    version: int = Field(default=0, ge=0)

    @field_validator("model")
    @classmethod
    def nonempty_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("模型名称不能为空")
        return value.strip()

    @field_validator("base_url", "ollama_base_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlparse(value)
        if value and (
            parsed.scheme not in ("https", "http")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("服务地址必须为不带账号、查询参数的 HTTP(S) URL")
        return value

    @model_validator(mode="after")
    def provider_requirements(self):
        if self.provider == "azure_openai" and not self.base_url:
            raise ValueError("Azure OpenAI 必须填写资源地址")
        return self


class LLMConfigResponse(BaseModel):
    """LLM 配置响应。"""

    provider: str
    model: str
    api_key: str
    base_url: str = ""
    api_version: str = "2024-10-21"
    ollama_base_url: str = "http://localhost:11434"
    temperature: float
    max_tokens: int
    mock_mode: bool
    smart_routing: bool
    version: int = 0


class LLMTestRequest(LLMConfigRequest):
    """LLM 连接测试请求。"""


class LLMTestResponse(BaseModel):
    """LLM 连接测试响应。"""

    success: bool
    message: str
    latency_ms: float | None = None


class NotificationChannel(BaseModel):
    """通知渠道配置。"""

    id: str
    type: Literal["email", "webhook", "slack"]
    name: str
    enabled: bool
    config: str

    @model_validator(mode="after")
    def validate_enabled_channel(self):
        if self.enabled:
            if self.type == "email":
                import re

                if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.config):
                    raise ValueError("邮箱地址无效")
            else:
                LLMConfigRequest.valid_url(self.config)
                if not self.config:
                    raise ValueError("启用通知渠道必须填写配置")
        return self


class NotificationSettingsRequest(BaseModel):
    """通知设置请求。"""

    channels: list[NotificationChannel]
    version: int = Field(default=0, ge=0)


class NotificationSettingsResponse(BaseModel):
    """通知设置响应。"""

    channels: list[NotificationChannel]


class OllamaModelInfo(BaseModel):
    """Ollama 模型信息。"""

    name: str
    size: str
    parameter_count: str = ""
    modified_at: str = ""


class OllamaModelListResponse(BaseModel):
    """Ollama 模型列表响应。"""

    models: list[OllamaModelInfo]
    available: bool
    message: str
