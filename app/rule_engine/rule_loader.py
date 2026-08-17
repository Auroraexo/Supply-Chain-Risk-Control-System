"""规则加载器。从数据库加载规则并构建内存缓存。"""

import structlog

from app.rule_engine.rule_executor import Rule, RulePrioritizer

logger = structlog.get_logger(__name__)


class RuleLoader:
    """规则加载器。

    从 DB 读取活跃规则 → 转换为 Rule 对象 → 内存缓存。
    支持热更新（变更通知刷新缓存）。
    """

    def __init__(self, rule_repo=None):
        self._rule_repo = rule_repo
        self._cache: RulePrioritizer | None = None

    async def load_rules(self) -> RulePrioritizer:
        """加载所有活跃规则。"""
        if self._cache is not None:
            return self._cache

        rules = await self._fetch_active_rules()
        self._cache = RulePrioritizer(rules)
        logger.info("rules_loaded", count=len(rules))
        return self._cache

    async def refresh(self) -> RulePrioritizer:
        """刷新缓存。"""
        self._cache = None
        return await self.load_rules()

    async def _fetch_active_rules(self) -> list[Rule]:
        """从数据库获取活跃规则。"""
        if self._rule_repo:
            db_rules = await self._rule_repo.get_active_rules()
            return [
                Rule(
                    rule_id=r.id,
                    rule_name=r.rule_name,
                    priority=r.priority,
                    enabled=r.is_active,
                    action={"type": r.action} if r.action else None,
                )
                for r in db_rules
            ]
        return []
