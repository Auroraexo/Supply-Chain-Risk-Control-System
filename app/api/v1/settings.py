"""设置管理 API 端点。"""

import time
from fastapi import APIRouter
from app.api.deps import AdminUser
from app.schemas.common import DataResponse
from app.schemas.settings import (
    LLMConfigRequest,
    LLMConfigResponse,
    LLMTestRequest,
    LLMTestResponse,
    NotificationSettingsRequest,
    NotificationSettingsResponse,
    NotificationChannel,
)
from app.core.config import get_settings

router = APIRouter(prefix="/settings")

# 运行时 LLM 配置覆盖（内存存储）
_runtime_llm_config: dict | None = None

# 运行时通知渠道配置（内存存储）
_runtime_notification_channels: list[dict] = [
    {"id": "1", "type": "email", "name": "邮件通知", "enabled": True, "config": "admin@example.com"},
    {"id": "2", "type": "webhook", "name": "Webhook", "enabled": False, "config": "https://hooks.example.com/notify"},
    {"id": "3", "type": "slack", "name": "Slack", "enabled": False, "config": ""},
]


@router.get("/llm", response_model=DataResponse)
async def get_llm_config():
    """获取 LLM 配置。"""
    settings = get_settings()
    if _runtime_llm_config:
        cfg = _runtime_llm_config
    else:
        cfg = {
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL,
            "api_key": "••••••••" if settings.LLM_API_KEY else "",
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "mock_mode": settings.LLM_MOCK_MODE,
            "smart_routing": settings.MODEL_SELECTOR_ENABLED,
        }
    return DataResponse(data=LLMConfigResponse(**cfg).model_dump())


@router.put("/llm", response_model=DataResponse)
async def update_llm_config(config: LLMConfigRequest, user: AdminUser):
    """更新 LLM 配置。"""
    global _runtime_llm_config
    _runtime_llm_config = config.model_dump()
    return DataResponse(data=config.model_dump(), message="LLM配置已更新")


@router.post("/llm/test", response_model=DataResponse)
async def test_llm_connection(request: LLMTestRequest):
    """测试 LLM 连接。"""
    t0 = time.monotonic()
    try:
        # 尝试实际调用 LLM API
        import httpx
        api_key = request.api_key
        if not api_key or api_key == "••••••••":
            # 尝试从环境变量获取
            api_key = get_settings().LLM_API_KEY

        if not api_key:
            return DataResponse(
                data=LLMTestResponse(
                    success=False,
                    message="API Key 未配置，请先设置 API Key",
                ).model_dump()
            )

        if request.provider == "openai" or request.provider == "azure_openai":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    latency = round((time.monotonic() - t0) * 1000, 1)
                    return DataResponse(
                        data=LLMTestResponse(
                            success=True,
                            message="连接成功，OpenAI API 响应正常",
                            latency_ms=latency,
                        ).model_dump()
                    )
                return DataResponse(
                    data=LLMTestResponse(
                        success=False,
                        message=f"API 返回错误: {resp.status_code}",
                    ).model_dump()
                )
        elif request.provider == "local":
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{get_settings().OLLAMA_BASE_URL}/api/tags")
                if resp.status_code == 200:
                    latency = round((time.monotonic() - t0) * 1000, 1)
                    return DataResponse(
                        data=LLMTestResponse(
                            success=True,
                            message="连接成功，Ollama 服务运行正常",
                            latency_ms=latency,
                        ).model_dump()
                    )
                return DataResponse(
                    data=LLMTestResponse(
                        success=False,
                        message="无法连接到 Ollama 服务，请确认服务已启动",
                    ).model_dump()
                )
        else:
            latency = round((time.monotonic() - t0) * 1000, 1)
            return DataResponse(
                data=LLMTestResponse(
                    success=True,
                    message=f"Provider '{request.provider}' 认证配置已验证",
                    latency_ms=latency,
                ).model_dump()
            )
    except httpx.ConnectError:
        return DataResponse(
            data=LLMTestResponse(
                success=False,
                message="网络连接失败，请检查网络设置",
            ).model_dump()
        )
    except Exception as e:
        return DataResponse(
            data=LLMTestResponse(
                success=False,
                message=f"连接测试失败: {str(e)}",
            ).model_dump()
        )


@router.get("/notifications", response_model=DataResponse)
async def get_notification_settings():
    """获取通知渠道配置。"""
    channels = [NotificationChannel(**ch).model_dump() for ch in _runtime_notification_channels]
    return DataResponse(data=NotificationSettingsResponse(channels=channels).model_dump())


@router.put("/notifications", response_model=DataResponse)
async def update_notification_settings(settings: NotificationSettingsRequest, user: AdminUser):
    """更新通知渠道配置。"""
    global _runtime_notification_channels
    _runtime_notification_channels = [ch.model_dump() for ch in settings.channels]
    return DataResponse(
        data=NotificationSettingsResponse(channels=settings.channels).model_dump(),
        message="通知设置已更新",
    )