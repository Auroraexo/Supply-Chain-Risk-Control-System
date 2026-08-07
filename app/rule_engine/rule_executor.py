"""规则执行器。

支持条件评估、模板变量替换、优先级排序。
"""
import time
import operator
from dataclasses import dataclass, field
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RuleCondition:
    field: str
    op: str
    value: Any
    logic: str = "AND"
    items: list["RuleCondition"] = field(default_factory=list)


@dataclass
class Rule:
    rule_id: str
    rule_name: str
    priority: int = 0
    enabled: bool = True
    conditions: Optional[RuleCondition] = None
    action: Optional[dict] = None


class RuleExecutor:
    """规则执行器。

    支持条件评估、模板变量替换、优先级排序。
    """

    OPERATORS = {
        "gt": operator.gt,
        "gte": operator.ge,
        "lt": operator.lt,
        "lte": operator.le,
        "eq": operator.eq,
        "neq": operator.ne,
        "in": lambda a, b: a in b,
        "contains": lambda a, b: b in a,
        "contains_any": lambda a, b: any(x in a for x in b) if isinstance(a, list) else False,
    }

    def evaluate(self, rule: Rule, context: dict) -> Optional[dict]:
        """评估单条规则，返回 action 或 None。"""
        t0 = time.monotonic()

        if not rule.enabled:
            logger.debug(
                "rule_executor.rule_disabled",
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
            )
            return None

        if not rule.conditions:
            logger.debug(
                "rule_executor.no_conditions",
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
            )
            return None

        logger.info(
            "rule_executor.evaluating",
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            priority=rule.priority,
            context_keys=list(context.keys()),
        )

        matched = self._evaluate_condition(rule.conditions, context, rule.rule_id)

        if matched:
            result = self._interpolate_action(rule.action, context) if rule.action else None
            logger.info(
                "rule_executor.matched",
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                priority=rule.priority,
                action=result.get("action") if result else None,
                elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
            )
            return result
        else:
            logger.debug(
                "rule_executor.not_matched",
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
            )
            return None

    def _evaluate_condition(self, condition: RuleCondition, context: dict, rule_id: str = "", depth: int = 0) -> bool:
        """递归评估条件树。"""
        prefix = "  " * depth

        if condition.items:
            t0 = time.monotonic()
            results = [self._evaluate_condition(item, context, rule_id, depth + 1) for item in condition.items]
            if condition.logic == "AND":
                result = all(results)
            elif condition.logic == "OR":
                result = any(results)
            elif condition.logic == "NOT":
                result = not results[0]
            else:
                result = False

            logger.debug(
                "rule_executor.group_eval",
                rule_id=rule_id,
                logic=condition.logic,
                child_count=len(condition.items),
                child_results=results,
                result=result,
                depth=depth,
                elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
            )
            return result

        field_value = self._get_nested_field(context, condition.field)
        op_func = self.OPERATORS.get(condition.op)
        if op_func is None:
            logger.warning(
                "rule_executor.unknown_operator",
                rule_id=rule_id,
                field=condition.field,
                operator=condition.op,
                depth=depth,
            )
            return False

        try:
            result = bool(op_func(field_value, condition.value))
            logger.debug(
                "rule_executor.leaf_eval",
                rule_id=rule_id,
                field=condition.field,
                operator=condition.op,
                field_value=field_value,
                expected=condition.value,
                result=result,
                depth=depth,
            )
            return result
        except (TypeError, ValueError) as e:
            logger.debug(
                "rule_executor.eval_error",
                rule_id=rule_id,
                field=condition.field,
                operator=condition.op,
                field_value=field_value,
                expected=condition.value,
                error=str(e),
                depth=depth,
            )
            return False

    def _get_nested_field(self, context: dict, field_path: str) -> Any:
        """支持嵌套字段访问，如 'order.amount'。"""
        keys = field_path.split(".")
        value = context
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _interpolate_action(self, action: dict, context: dict) -> dict:
        """模板变量替换。"""
        import re
        result = action.copy()
        reason = action.get("reason", "")
        for match in re.finditer(r"\{(\w+)\}", reason):
            var_name = match.group(1)
            value = self._get_nested_field(context, var_name)
            reason = reason.replace(match.group(0), str(value) if value is not None else "N/A")
        result["reason"] = reason
        return result


class RulePrioritizer:
    """规则优先级排序器。"""

    def __init__(self, rules: list[Rule]):
        t0 = time.monotonic()
        self._rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        logger.info(
            "rule_prioritizer.initialized",
            total_rules=len(rules),
            enabled_rules=sum(1 for r in rules if r.enabled),
            top_priority=self._rules[0].priority if self._rules else 0,
            rule_ids=[r.rule_id for r in self._rules[:5]],
            elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
        )

    def execute(self, context: dict) -> Optional[dict]:
        """按优先级执行规则，返回第一个匹配的动作。"""
        flow_start = time.monotonic()
        executor = RuleExecutor()

        for i, rule in enumerate(self._rules):
            if i < 100:  # 避免日志过多，前100条规则记录详细日志
                logger.debug(
                    "rule_prioritizer.trying",
                    rule_index=i,
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    priority=rule.priority,
                )

            result = executor.evaluate(rule, context)
            if result is not None:
                logger.info(
                    "rule_prioritizer.matched",
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    priority=rule.priority,
                    checked_count=i + 1,
                    total_rules=len(self._rules),
                    elapsed_ms=round((time.monotonic() - flow_start) * 1000, 1),
                )
                return result

        logger.info(
            "rule_prioritizer.no_match",
            checked_count=len(self._rules),
            context_keys=list(context.keys()),
            elapsed_ms=round((time.monotonic() - flow_start) * 1000, 1),
        )
        return None