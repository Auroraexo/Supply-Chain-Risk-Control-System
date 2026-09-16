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
    OllamaModelListResponse,
    OllamaModelInfo,
    NotificationSettingsRequest,
    NotificationSettingsResponse,
    NotificationChannel,
)
from app.core.config import get_effective_llm_config, get_settings, set_runtime_llm_config

router = APIRouter(prefix="/settings")

# 运行时通知渠道配置（内存存储）
_runtime_notification_channels: list[dict] = [
    {"id": "1", "type": "email", "name": "邮件通知", "enabled": True, "config": "admin@example.com"},
    {"id": "2", "type": "webhook", "name": "Webhook", "enabled": False, "config": "https://hooks.example.com/notify"},
    {"id": "3", "type": "slack", "name": "Slack", "enabled": False, "config": ""},
]


def _human_size(num_bytes: int) -> str:
    """将字节数转换为可读格式。"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


@router.get("/llm", response_model=DataResponse)
async def get_llm_config():
    """获取 LLM 配置。"""
    cfg = get_effective_llm_config()
    cfg["api_key"] = "••••••••" if cfg.get("api_key") else ""
    return DataResponse(data=LLMConfigResponse(**cfg).model_dump())


@router.put("/llm", response_model=DataResponse)
async def update_llm_config(config: LLMConfigRequest, user: AdminUser):
    """更新 LLM 配置。"""
    cfg = config.model_dump()
    # 如果 API Key 是占位符，不覆盖真实值
    if cfg["api_key"] == "••••••••":
        cfg["api_key"] = get_effective_llm_config().get("api_key", "")
    set_runtime_llm_config(cfg)
    # Import lazily so the settings endpoint does not make optional model
    # runtime dependencies a server-startup requirement.
    from app.core.llm import get_llm
    get_llm.cache_clear()
    response_cfg = {**cfg, "api_key": "••••••••" if cfg.get("api_key") else ""}
    return DataResponse(data=response_cfg, message="LLM配置已更新")


@router.post("/llm/test", response_model=DataResponse)
async def test_llm_connection(request: LLMTestRequest):
    """测试 LLM 连接。"""
    import httpx

    t0 = time.monotonic()
    try:
        api_key = request.api_key
        effective = get_effective_llm_config()
        if not api_key or api_key == "••••••••":
            api_key = effective.get("api_key", "")

        # Ollama 本地模型不需要 API Key
        if request.provider == "local":
            ollama_url = (request.ollama_base_url or effective.get("ollama_base_url") or get_settings().OLLAMA_BASE_URL).rstrip("/")
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    model_count = len(data.get("models", []))
                    latency = round((time.monotonic() - t0) * 1000, 1)
                    return DataResponse(
                        data=LLMTestResponse(
                            success=True,
                            message=f"Ollama 服务运行正常，发现 {model_count} 个模型",
                            latency_ms=latency,
                        ).model_dump()
                    )
                return DataResponse(
                    data=LLMTestResponse(
                        success=False,
                        message=f"无法连接到 Ollama 服务 ({resp.status_code})，请确认服务已启动并在端口 11434 监听",
                    ).model_dump()
                )

        if not api_key:
            return DataResponse(
                data=LLMTestResponse(
                    success=False,
                    message="API Key 未配置，请先设置 API Key",
                ).model_dump()
            )

        if request.provider == "openai":
            base_url = request.base_url or effective.get("base_url") or "https://api.openai.com/v1"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base_url.rstrip('/')}/models",
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
                        message=f"API 返回错误: {resp.status_code} - {resp.text[:200]}",
                    ).model_dump()
                )

        elif request.provider == "azure_openai":
            base_url = request.base_url or effective.get("base_url") or ""
            if not base_url:
                return DataResponse(data=LLMTestResponse(success=False, message="Azure OpenAI 需要填写 Base URL").model_dump())
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base_url.rstrip('/')}/openai/deployments?api-version={request.api_version}",
                    headers={"api-key": api_key},
                )
                if resp.status_code == 200:
                    latency = round((time.monotonic() - t0) * 1000, 1)
                    return DataResponse(
                        data=LLMTestResponse(
                            success=True,
                        message="连接成功，Azure OpenAI 端点响应正常",
                            latency_ms=latency,
                        ).model_dump()
                    )
                return DataResponse(
                    data=LLMTestResponse(
                        success=False,
                        message=f"API 返回错误: {resp.status_code}",
                    ).model_dump()
                )

        elif request.provider == "anthropic":
            base_url = request.base_url or effective.get("base_url") or "https://api.anthropic.com"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base_url.rstrip('/')}/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                if resp.status_code == 200:
                    latency = round((time.monotonic() - t0) * 1000, 1)
                    return DataResponse(
                        data=LLMTestResponse(
                            success=True,
                            message="连接成功，Anthropic API 响应正常",
                            latency_ms=latency,
                        ).model_dump()
                    )
                return DataResponse(
                    data=LLMTestResponse(
                        success=False,
                        message=f"API 返回错误: {resp.status_code}",
                    ).model_dump()
                )

        else:
            latency = round((time.monotonic() - t0) * 1000, 1)
            return DataResponse(
                data=LLMTestResponse(
                    success=True,
                    message=f"Provider '{request.provider}' 配置已验证",
                    latency_ms=latency,
                ).model_dump()
            )

    except httpx.ConnectError:
        return DataResponse(
            data=LLMTestResponse(
                success=False,
                message="网络连接失败，请检查服务地址和网络设置",
            ).model_dump()
        )
    except httpx.TimeoutException:
        return DataResponse(
            data=LLMTestResponse(
                success=False,
                message="连接超时，请检查服务是否正常运行",
            ).model_dump()
        )
    except Exception as e:
        return DataResponse(
            data=LLMTestResponse(
                success=False,
                message=f"连接测试失败: {str(e)}",
            ).model_dump()
        )


@router.get("/llm/ollama-models", response_model=DataResponse)
async def list_ollama_models(base_url: str = "http://localhost:11434"):
    """获取 Ollama 本地可用模型列表。"""
    import httpx

    try:
        ollama_url = base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            if resp.status_code != 200:
                return DataResponse(
                    data=OllamaModelListResponse(
                        models=[],
                        available=False,
                        message=f"无法连接 Ollama (HTTP {resp.status_code})",
                    ).model_dump()
                )

            data = resp.json()
            raw_models = data.get("models", [])
            models: list[OllamaModelInfo] = []
            for m in raw_models:
                models.append(OllamaModelInfo(
                    name=m.get("name", ""),
                    size=_human_size(m.get("size", 0)),
                    parameter_count=m.get("details", {}).get("parameter_size", ""),
                    modified_at=m.get("modified_at", ""),
                ))
            return DataResponse(
                data=OllamaModelListResponse(
                    models=models,
                    available=True,
                    message=f"发现 {len(models)} 个可用模型",
                ).model_dump()
            )

    except httpx.ConnectError:
        return DataResponse(
            data=OllamaModelListResponse(
                models=[],
                available=False,
                message="无法连接到 Ollama 服务。请先安装并启动: https://ollama.com/download",
            ).model_dump()
        )
    except httpx.TimeoutException:
        return DataResponse(
            data=OllamaModelListResponse(
                models=[],
                available=False,
                message="连接 Ollama 超时，请检查服务是否在运行",
            ).model_dump()
        )
    except Exception as e:
        return DataResponse(
            data=OllamaModelListResponse(
                models=[],
                available=False,
                message=f"获取模型列表失败: {str(e)}",
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
