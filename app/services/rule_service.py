"""规则管理服务。"""
import time
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.rule_repo import RuleRepository
from app.models.rule_node import RuleNode, RuleType, LogicOp
from app.schemas.rule import RuleCreateRequest, RuleUpdateRequest
from app.core.exceptions import NotFoundException, ValidationException
import structlog

logger = structlog.get_logger(__name__)


class RuleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_repo = RuleRepository(db)

    async def get_rules(self, page: int = 1, page_size: int = 20, is_active: bool | None = None) -> tuple[list[dict], int]:
        if is_active is not None:
            rules = await self.rule_repo.get_active_rules()
        else:
            rules = await self.rule_repo.get_all(skip=(page - 1) * page_size, limit=page_size)
        total = await self.rule_repo.count()
        return (
            [self._rule_to_dict(r) for r in rules],
            total,
        )

    async def get_tree(self) -> list[dict]:
        roots = await self.rule_repo.get_root_nodes()
        if not roots:
            return []
        return [self._rule_to_dict(root, include_children=True) for root in roots]

    async def create_rule(self, request: RuleCreateRequest) -> dict:
        rule = RuleNode(
            rule_name=request.rule_name,
            rule_type=RuleType(request.rule_type),
            parent_id=request.parent_id,
            condition_type=request.condition_type,
            field_name=request.field_name,
            operator=request.operator,
            threshold_value=request.threshold_value,
            logic_op=LogicOp(request.logic_op),
            weight=request.weight,
            action=request.action,
            action_params=request.action_params,
            priority=request.priority,
            description=request.description,
        )
        rule = await self.rule_repo.create(rule)

        # 创建初始版本快照
        await self.rule_repo.create_version(
            rule_id=rule.id,
            version=1,
            snapshot=self._rule_to_dict(rule),
            change_reason="初始创建",
        )
        await self.db.commit()

        logger.info("rule_service.created", rule_id=rule.id, rule_name=rule.rule_name)
        return self._rule_to_dict(rule)

    async def update_rule(self, rule_id: str, request: RuleUpdateRequest) -> dict:
        existing = await self.rule_repo.get_by_id(rule_id)
        if not existing:
            raise NotFoundException(f"规则未找到: {rule_id}")

        values = request.model_dump(exclude_unset=True)
        # 将字符串转换为枚举类型，避免 SQLAlchemy bulk update 后 enum 字段为字符串
        if "rule_type" in values:
            values["rule_type"] = RuleType(values["rule_type"])
        if "logic_op" in values:
            values["logic_op"] = LogicOp(values["logic_op"])
        updated = await self.rule_repo.update(rule_id, values)
        if not updated:
            raise NotFoundException(f"规则更新失败: {rule_id}")

        # 创建新版本快照
        versions = await self.rule_repo.get_versions(rule_id)
        next_version = (versions[0].version + 1) if versions else 1
        await self.rule_repo.create_version(
            rule_id=rule_id,
            version=next_version,
            snapshot=self._rule_to_dict(updated),
            change_reason=f"更新字段: {list(values.keys())}",
        )
        await self.db.commit()

        logger.info("rule_service.updated", rule_id=rule_id, version=next_version)
        return self._rule_to_dict(updated)

    async def delete_rule(self, rule_id: str) -> None:
        await self.rule_repo.toggle_active(rule_id, False)
        await self.db.commit()
        logger.info("rule_service.deleted", rule_id=rule_id)

    async def toggle_rule(self, rule_id: str, is_active: bool) -> dict:
        rule = await self.rule_repo.toggle_active(rule_id, is_active)
        if not rule:
            raise NotFoundException(f"规则未找到: {rule_id}")
        await self.db.commit()
        return self._rule_to_dict(rule)

    async def get_versions(self, rule_id: str) -> list[dict]:
        """获取规则版本历史。"""
        versions = await self.rule_repo.get_versions(rule_id)
        return [
            {
                "version": v.version,
                "snapshot": v.snapshot,
                "changed_by": v.changed_by,
                "change_reason": v.change_reason,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    async def rollback(self, rule_id: str, version: int) -> dict:
        """回滚规则到指定版本。"""
        rule = await self.rule_repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundException(f"规则未找到: {rule_id}")

        versions = await self.rule_repo.get_versions(rule_id)
        target = next((v for v in versions if v.version == version), None)
        if not target:
            raise NotFoundException(f"版本未找到: rule_id={rule_id}, version={version}")

        snapshot = target.snapshot
        updatable_fields = {
            "rule_name": snapshot.get("rule_name"),
            "rule_type": snapshot.get("rule_type"),
            "parent_id": snapshot.get("parent_id"),
            "condition_type": snapshot.get("condition_type"),
            "field_name": snapshot.get("field_name"),
            "operator": snapshot.get("operator"),
            "threshold_value": snapshot.get("threshold_value"),
            "logic_op": snapshot.get("logic_op"),
            "weight": snapshot.get("weight"),
            "action": snapshot.get("action"),
            "action_params": snapshot.get("action_params"),
            "priority": snapshot.get("priority"),
            "description": snapshot.get("description"),
        }
        # 过滤掉 None 值
        updatable_fields = {k: v for k, v in updatable_fields.items() if v is not None}

        updated = await self.rule_repo.update(rule_id, updatable_fields)
        if not updated:
            raise NotFoundException(f"规则更新失败: {rule_id}")

        # 创建回滚版本快照
        next_version = (versions[0].version + 1) if versions else 1
        await self.rule_repo.create_version(
            rule_id=rule_id,
            version=next_version,
            snapshot=self._rule_to_dict(updated),
            change_reason=f"回滚至版本 {version}",
        )
        await self.db.commit()

        logger.info("rule_service.rolled_back", rule_id=rule_id, from_version=next_version, to_version=version)
        return self._rule_to_dict(updated)

    def _rule_to_dict(self, rule: RuleNode, include_children: bool = False) -> dict:
        data = {
            "id": rule.id,
            "rule_name": rule.rule_name,
            "rule_type": rule.rule_type.value if hasattr(rule.rule_type, "value") else rule.rule_type,
            "parent_id": rule.parent_id,
            "condition_type": rule.condition_type,
            "field_name": rule.field_name,
            "operator": rule.operator,
            "threshold_value": rule.threshold_value,
            "logic_op": rule.logic_op.value if hasattr(rule.logic_op, "value") else rule.logic_op,
            "weight": rule.weight,
            "action": rule.action,
            "priority": rule.priority,
            "is_active": rule.is_active,
            "version": rule.version,
            "description": rule.description,
            "children": [],
        }
        if include_children and rule.children:
            data["children"] = [self._rule_to_dict(child, include_children=True) for child in rule.children]
        return data