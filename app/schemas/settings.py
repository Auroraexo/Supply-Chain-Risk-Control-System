"""设置相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class LLMConfigRequest(BaseModel):
    """LLM 配置请求。"""
    provider: str = Field(default="openai", description="LLM提供商")
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    api_key: str = Field(default="", description="API密钥")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=4096, ge=1, le=128000, description="最大Token数")
    mock_mode: bool = Field(default=False, description="Mock模式")
    smart_routing: bool = Field(default=False, description="智能路由")


class LLMConfigResponse(BaseModel):
    """LLM 配置响应。"""
    provider: str
    model: str
    api_key: str
    temperature: float
    max_tokens: int
    mock_mode: bool
    smart_routing: bool


class LLMTestRequest(BaseModel):
    """LLM 连接测试请求。"""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""


class LLMTestResponse(BaseModel):
    """LLM 连接测试响应。"""
    success: bool
    message: str
    latency_ms: float | None = None


class NotificationChannel(BaseModel):
    """通知渠道配置。"""
    id: str
    type: str
    name: str
    enabled: bool
    config: str


class NotificationSettingsRequest(BaseModel):
    """通知设置请求。"""
    channels: list[NotificationChannel]


class NotificationSettingsResponse(BaseModel):
    """通知设置响应。"""
    channels: list[NotificationChannel]