"""Database-backed, encrypted settings with optimistic concurrency control."""

import json

from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.audit_event import AuditEvent
from app.models.system_setting import SettingRevision, SystemSetting


def settings_cipher() -> Fernet:
    key = get_settings().SETTINGS_ENCRYPTION_KEY
    if not key:
        raise HTTPException(503, "请配置 SETTINGS_ENCRYPTION_KEY 后再保存系统设置")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise HTTPException(503, "SETTINGS_ENCRYPTION_KEY 格式无效") from exc


class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def read(self, key: str) -> tuple[dict | None, int]:
        row = await self.db.get(SystemSetting, key)
        if row is None:
            return None, 0
        # A missing key must not block unrelated read-only/dev requests; any
        # persisted secret remains unreadable until the operator restores it.
        try:
            value = json.loads(settings_cipher().decrypt(row.encrypted_value.encode()))
        except HTTPException:
            return None, row.version
        return value, row.version

    async def write(self, key: str, value: dict, actor: str, expected_version: int) -> int:
        encrypted = settings_cipher().encrypt(json.dumps(value).encode()).decode()
        version = expected_version + 1
        if expected_version == 0:
            self.db.add(
                SystemSetting(key=key, encrypted_value=encrypted, version=version, updated_by=actor)
            )
        else:
            result = await self.db.execute(
                update(SystemSetting)
                .where(SystemSetting.key == key, SystemSetting.version == expected_version)
                .values(encrypted_value=encrypted, version=version, updated_by=actor)
            )
            if result.rowcount != 1:
                raise HTTPException(409, "配置已被其他用户更新，请重新加载")
        self.db.add(
            SettingRevision(key=key, encrypted_value=encrypted, version=version, updated_by=actor)
        )
        self.db.add(
            AuditEvent(
                entity_id=f"settings.{key}",
                action="settings.update",
                actor=actor,
                before={"version": expected_version},
                after={"version": version},
            )
        )
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(409, "配置已被其他用户更新，请重新加载") from exc
        return version

    async def history(self, key: str) -> list[dict]:
        rows = (
            (
                await self.db.execute(
                    select(SettingRevision)
                    .where(SettingRevision.key == key)
                    .order_by(SettingRevision.version.desc())
                    .limit(50)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "version": r.version,
                "updated_by": r.updated_by,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
