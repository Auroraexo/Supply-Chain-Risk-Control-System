"""DSL 解析器。

将 YAML/JSON 格式的规则定义解析为 Rule 对象。
"""
import time

import structlog
import yaml

from app.rule_engine.rule_executor import Rule, RuleCondition

logger = structlog.get_logger(__name__)


class DSLParser:
    """规则 DSL 解析器。"""

    @staticmethod
    def parse_yaml(yaml_content: str) -> Rule:
        """从 YAML 字符串解析规则。"""
        t0 = time.monotonic()
        logger.info("dsl_parser.yaml_parse_start", content_length=len(yaml_content))
        try:
            data = yaml.safe_load(yaml_content)
            rule = DSLParser._parse_dict(data)
            logger.info(
                "dsl_parser.yaml_parse_complete",
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                priority=rule.priority,
                has_conditions=rule.conditions is not None,
                has_action=rule.action is not None,
                elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
            )
            return rule
        except yaml.YAMLError as e:
            logger.error(
                "dsl_parser.yaml_parse_error",
                error=str(e),
                content_preview=yaml_content[:100],
                exc_info=True,
            )
            raise ValueError(f"YAML 解析失败: {e}") from e

    @staticmethod
    def parse_dict(data: dict) -> Rule:
        """从字典解析规则。"""
        t0 = time.monotonic()
        logger.info("dsl_parser.dict_parse_start", keys=list(data.keys()))
        rule = DSLParser._parse_dict(data)
        logger.info(
            "dsl_parser.dict_parse_complete",
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            priority=rule.priority,
            elapsed_ms=round((time.monotonic() - t0) * 1000, 1),
        )
        return rule

    @staticmethod
    def _parse_dict(data: dict) -> Rule:
        """内部解析逻辑。"""
        rule = Rule(
            rule_id=data.get("rule_id", ""),
            rule_name=data.get("rule_name", ""),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
        )

        if not rule.rule_id:
            logger.warning("dsl_parser.missing_rule_id", rule_name=data.get("rule_name"))
        if not rule.rule_name:
            logger.warning("dsl_parser.missing_rule_name", rule_id=rule.rule_id)

        conditions = data.get("conditions")
        if conditions:
            condition_count = DSLParser._count_conditions(conditions)
            logger.debug(
                "dsl_parser.parsing_conditions",
                rule_id=rule.rule_id,
                condition_count=condition_count,
            )
            rule.conditions = DSLParser._parse_conditions(conditions)
        else:
            logger.debug("dsl_parser.no_conditions", rule_id=rule.rule_id)

        rule.action = data.get("action")
        if rule.action:
            logger.debug(
                "dsl_parser.action_parsed",
                rule_id=rule.rule_id,
                action_keys=list(rule.action.keys()),
            )
        else:
            logger.debug("dsl_parser.no_action", rule_id=rule.rule_id)

        return rule

    @staticmethod
    def _parse_conditions(data: dict) -> RuleCondition:
        """递归解析条件。"""
        condition = RuleCondition(
            field=data.get("field", ""),
            op=data.get("operator", "eq"),
            value=data.get("value"),
            logic=data.get("logic", "AND"),
        )

        items = data.get("items", [])
        if items:
            condition.items = [DSLParser._parse_conditions(item) for item in items]
            logger.debug(
                "dsl_parser.condition_group_parsed",
                field=condition.field,
                logic=condition.logic,
                child_count=len(items),
            )

        return condition

    @staticmethod
    def _count_conditions(data: dict) -> int:
        """递归统计条件总数。"""
        count = 0
        items = data.get("items", [])
        if items:
            for item in items:
                count += DSLParser._count_conditions(item)
        else:
            if data.get("field"):
                count = 1
        return count
