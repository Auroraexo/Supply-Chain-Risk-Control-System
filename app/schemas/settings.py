"""设置相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class LLMConfigRequest(BaseModel):
    """LLM 配置请求。"""
    provider: str = Field(default="openai", description="LLM提供商")
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    api_key: str = Field(default="", description="API密钥")
    base_url: str = Field(default="", description="Provider API 基础地址")
    api_version: str = Field(default="2024-10-21", description="Azure OpenAI API 版本")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama 服务地址")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    max_tokens: int = Field(default=4096, ge=1, le=128000, description="最大Token数")
    mock_mode: bool = Field(default=False, description="Mock模式")
    smart_routing: bool = Field(default=False, description="智能路由")


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


class LLMTestRequest(BaseModel):
    """LLM 连接测试请求。"""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    api_version: str = "2024-10-21"
    ollama_base_url: str = "http://localhost:11434"


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
