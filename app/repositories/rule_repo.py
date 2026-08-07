from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.rule_node import RuleNode
from app.models.rule_version import RuleVersion
from app.repositories.base import BaseRepository

class RuleRepository(BaseRepository[RuleNode]):
    def __init__(self, db: AsyncSession):
        super().__init__(RuleNode, db)

    async def get_children(self, parent_id: str) -> list[RuleNode]:
        result = await self.db.execute(
            select(RuleNode).where(RuleNode.parent_id == parent_id).order_by(RuleNode.priority.desc())
        )
        return list(result.scalars().all())

    async def get_root_nodes(self) -> list[RuleNode]:
        result = await self.db.execute(
            select(RuleNode).where(RuleNode.parent_id.is_(None), RuleNode.is_active.is_(True)).order_by(RuleNode.priority.desc())
        )
        return list(result.scalars().all())

    async def get_active_rules(self) -> list[RuleNode]:
        result = await self.db.execute(
            select(RuleNode).where(RuleNode.is_active.is_(True)).order_by(RuleNode.priority.desc())
        )
        return list(result.scalars().all())

    async def toggle_active(self, rule_id: str, is_active: bool) -> RuleNode | None:
        return await self.update(rule_id, {"is_active": is_active})

    async def get_versions(self, rule_id: str) -> list[RuleVersion]:
        result = await self.db.execute(
            select(RuleVersion)
            .where(RuleVersion.rule_id == rule_id)
            .order_by(desc(RuleVersion.version))
        )
        return list(result.scalars().all())

    async def create_version(self, rule_id: str, version: int, snapshot: dict, changed_by: str | None = None, change_reason: str | None = None) -> RuleVersion:
        rv = RuleVersion(
            rule_id=rule_id,
            version=version,
            snapshot=snapshot,
            changed_by=changed_by,
            change_reason=change_reason,
        )
        self.db.add(rv)
        await self.db.flush()
        await self.db.refresh(rv)
        return rv