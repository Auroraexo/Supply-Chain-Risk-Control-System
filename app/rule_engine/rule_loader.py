"""规则加载器。从数据库加载规则并构建内存缓存。"""

import structlog

from app.rule_engine.rule_executor import Rule, RuleCondition, RulePrioritizer

logger = structlog.get_logger(__name__)


class RuleLoader:
    """规则加载器。

    从 DB 读取活跃规则的根节点 → 将 rule_nodes 树转换为 Rule/RuleCondition
    条件树 → 构建 RulePrioritizer 内存缓存。
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
        """从数据库获取活跃规则，并转换为 Rule 对象。

        每个根节点（parent_id is None）对应一条规则；
        根节点的子树被递归转换为 RuleCondition 条件树。
        """
        if not self._rule_repo:
            return []

        root_nodes = await self._rule_repo.get_root_nodes()
        rules: list[Rule] = []
        for root in root_nodes:
            rule = self._node_to_rule(root)
            if rule is not None:
                rules.append(rule)
        return rules

    def _node_to_rule(self, node) -> Rule | None:
        """将根 RuleNode 转换为 Rule 对象。

        Returns:
            转换后的 Rule；若节点的子规则没有可评估条件或 action，返回 None
        """
        conditions = self._build_conditions(node)
        action = self._extract_action(node)
        if conditions is None and action is None:
            # 既不产生条件也不产生动作的规则无意义，跳过
            logger.debug(
                "rule_loader.skipped_empty_rule",
                rule_id=getattr(node, "id", ""),
                rule_name=getattr(node, "rule_name", ""),
            )
            return None

        return Rule(
            rule_id=getattr(node, "id", ""),
            rule_name=getattr(node, "rule_name", ""),
            priority=getattr(node, "priority", 0),
            enabled=getattr(node, "is_active", True),
            conditions=conditions,
            action=action,
        )

    def _build_conditions(self, node) -> RuleCondition | None:
        """递归构建条件树。

        规则：
        - condition 节点（有 field_name）→ 叶子条件
        - group 节点（有 children 且无 field_name）→ 按 logic_op 组合子条件
        - action 节点 → 不产生条件
        """
        rule_type = getattr(getattr(node, "rule_type", None), "value", None) or getattr(
            node, "rule_type", None
        )
        field_name = getattr(node, "field_name", None)

        if rule_type == "action":
            return None

        if field_name:
            # 叶子条件节点
            return RuleCondition(
                field=field_name,
                op=getattr(node, "operator", "eq") or "eq",
                value=self._coerce_threshold(getattr(node, "threshold_value", None)),
                logic="AND",
            )

        # group 节点：组合子节点
        children = getattr(node, "children", None) or []
        if not children:
            return None

        child_conditions = []
        for child in children:
            cond = self._build_conditions(child)
            if cond is not None:
                child_conditions.append(cond)

        if not child_conditions:
            return None

        logic_op = getattr(getattr(node, "logic_op", None), "value", None) or "AND"
        return RuleCondition(
            field="",
            op="",
            value=None,
            logic=logic_op if logic_op in ("AND", "OR", "NOT") else "AND",
            items=child_conditions,
        )

    def _extract_action(self, node) -> dict | None:
        """递归查找子树中的 action 节点，提取 action。"""
        rule_type = getattr(getattr(node, "rule_type", None), "value", None) or getattr(
            node, "rule_type", None
        )
        if rule_type == "action" and getattr(node, "action", None):
            return {"action": node.action, "params": getattr(node, "action_params", None)}

        for child in getattr(node, "children", None) or []:
            action = self._extract_action(child)
            if action is not None:
                return action
        return None

    @staticmethod
    def _coerce_threshold(value):
        """将阈值字符串转换为合适的数值类型（int/float/str）。"""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                return value
        return value
