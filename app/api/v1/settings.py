"""Encrypted, versioned administrator settings and real inference diagnostics."""

import asyncio
import json
import time

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import AdminUser, DBSession
from app.core.config import get_effective_llm_config, request_llm_config
from app.models.system_setting import SettingRevision
from app.schemas.common import DataResponse
from app.schemas.settings import (
    LLMConfigRequest,
    LLMConfigResponse,
    LLMTestRequest,
    LLMTestResponse,
    NotificationSettingsRequest,
)
from app.services.settings_service import SettingsService, settings_cipher

router = APIRouter(prefix="/settings")
MASK = "••••••••"
DEFAULT_CHANNELS = [
    {"id": "1", "type": "email", "name": "邮件通知", "enabled": False, "config": ""},
    {"id": "2", "type": "webhook", "name": "Webhook", "enabled": False, "config": ""},
    {"id": "3", "type": "slack", "name": "Slack", "enabled": False, "config": ""},
]


def public_config(cfg: dict, version: int) -> dict:
    return LLMConfigResponse(
        **{**cfg, "api_key": MASK if cfg.get("api_key") else "", "version": version}
    ).model_dump()


def resolve_key(cfg: dict, effective: dict) -> dict:
    if cfg["api_key"] == MASK:
        if cfg["provider"] != effective["provider"]:
            raise HTTPException(422, "切换模型提供商后必须重新填写 API Key")
        cfg["api_key"] = effective.get("api_key", "")
    if cfg["provider"] != "local" and not cfg["api_key"]:
        raise HTTPException(422, "云端模型必须填写 API Key")
    if cfg["provider"] == "local":
        cfg["api_key"] = ""
    return cfg


@router.get("/llm", response_model=DataResponse)
async def get_llm_config(db: DBSession, user: AdminUser):
    cfg, version = await SettingsService(db).read("llm")
    return DataResponse(data=public_config(cfg or get_effective_llm_config(), version))


@router.put("/llm", response_model=DataResponse)
async def update_llm_config(config: LLMConfigRequest, db: DBSession, user: AdminUser):
    cfg = resolve_key(config.model_dump(exclude={"version"}), get_effective_llm_config())
    version = await SettingsService(db).write("llm", cfg, user["sub"], config.version)
    await db.commit()
    request_llm_config.set(cfg)
    return DataResponse(data=public_config(cfg, version), message="配置已加密保存，下次调用生效")


@router.get("/llm/history", response_model=DataResponse)
async def llm_history(db: DBSession, user: AdminUser):
    return DataResponse(data=await SettingsService(db).history("llm"))


@router.post("/llm/rollback/{version}", response_model=DataResponse)
async def rollback_llm(version: int, config: LLMConfigRequest, db: DBSession, user: AdminUser):
    row = (
        await db.execute(
            select(SettingRevision).where(
                SettingRevision.key == "llm", SettingRevision.version == version
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "配置版本不存在")
    cfg = json.loads(settings_cipher().decrypt(row.encrypted_value.encode()))
    new_version = await SettingsService(db).write("llm", cfg, user["sub"], config.version)
    await db.commit()
    return DataResponse(data=public_config(cfg, new_version), message="配置已回滚")


@router.post("/llm/test", response_model=DataResponse)
async def test_llm_connection(request: LLMTestRequest, db: DBSession, user: AdminUser):
    from app.core.llm import build_llm

    cfg = resolve_key(request.model_dump(exclude={"version"}), get_effective_llm_config())
    cfg.update(mock_mode=False, max_tokens=16, temperature=0)
    start = time.monotonic()
    try:
        model = build_llm(cfg)
        async with asyncio.timeout(30):
            result = await model.ainvoke("Reply with only OK.")
        if not result.content:
            raise ValueError("模型返回空内容")
        data = LLMTestResponse(
            success=True,
            message=f"指定模型 {cfg['model']} 已完成真实推理",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )
    except Exception as exc:
        # Provider response bodies can include submitted keys or URLs.
        status = getattr(exc, "status_code", None)
        labels = {
            401: "API Key 无效",
            403: "模型权限不足",
            404: "模型或端点不存在",
            429: "请求限流或额度不足",
        }
        message = labels.get(status, "推理失败，请核对模型名称、服务地址和提供商参数")
        if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
            message = "模型推理超时"
        data = LLMTestResponse(
            success=False, message=message, latency_ms=round((time.monotonic() - start) * 1000, 1)
        )
    return DataResponse(data=data.model_dump())


def human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return ""


@router.get("/llm/ollama-models", response_model=DataResponse)
async def list_ollama_models(user: AdminUser, base_url: str = "http://localhost:11434"):
    try:
        base_url = LLMConfigRequest.valid_url(base_url)
    except ValueError as exc:
        raise HTTPException(422, "无效的 Ollama URL") from exc
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
        models = [
            {
                "name": m["name"],
                "size": human_size(m.get("size", 0)),
                "parameter_count": "",
                "modified_at": m.get("modified_at", ""),
            }
            for m in resp.json().get("models", [])
        ]
        return DataResponse(
            data={"models": models, "available": True, "message": f"发现 {len(models)} 个模型"}
        )
    except (httpx.HTTPError, ValueError, KeyError):
        return DataResponse(
            data={
                "models": [],
                "available": False,
                "message": "无法获取 Ollama 模型，请检查服务地址和连接",
            }
        )


@router.get("/notifications", response_model=DataResponse)
async def get_notification_settings(db: DBSession, user: AdminUser):
    value, version = await SettingsService(db).read("notifications")
    return DataResponse(data={**(value or {"channels": DEFAULT_CHANNELS}), "version": version})


@router.put("/notifications", response_model=DataResponse)
async def update_notification_settings(
    settings: NotificationSettingsRequest, db: DBSession, user: AdminUser
):
    value = settings.model_dump(exclude={"version"})
    version = await SettingsService(db).write("notifications", value, user["sub"], settings.version)
    return DataResponse(data={**value, "version": version}, message="通知设置已加密保存")
