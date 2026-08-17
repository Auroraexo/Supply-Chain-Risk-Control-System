"""规则引擎层单元测试。

覆盖 rule_engine 模块的纯逻辑组件（无需真实 DB）：
- RuleExecutor（条件树求值、操作符、嵌套 AND/OR/NOT）
- RulePrioritizer（优先级排序、首命中、无命中）
- DSLParser（dict/YAML → Rule 对象的解析）
- DecisionTreeWalker._evaluate（条件节点求值）
- DecisionTreeWalker.walk（用 mock repo 测遍历与条件分支）
"""

import asyncio

from app.rule_engine.dsl_parser import DSLParser
from app.rule_engine.rule_executor import (
    Rule,
    RuleCondition,
    RuleExecutor,
    RulePrioritizer,
)
from app.rule_engine.tree_walker import DecisionTreeWalker

# ──────────────────────────────────────────────
# RuleExecutor：条件树求值
# ──────────────────────────────────────────────

def _make_rule(rule_id="r1", conditions=None, action=None, priority=0, enabled=True):
    return Rule(
        rule_id=rule_id,
        rule_name=f"规则 {rule_id}",
        priority=priority,
        enabled=enabled,
        conditions=conditions,
        action=action,
    )


def test_rule_executor_leaf_condition_gt():
    executor = RuleExecutor()
    rule = _make_rule(
        conditions=RuleCondition(field="risk_score", op="gt", value=50),
        action={"action": "escalate", "reason": "高风险"},
    )
    result = executor.evaluate(rule, {"risk_score": 80})
    assert result is not None
    assert result["action"] == "escalate"


def test_rule_executor_leaf_condition_not_matched():
    executor = RuleExecutor()
    rule = _make_rule(
        conditions=RuleCondition(field="risk_score", op="gt", value=50),
        action={"action": "escalate"},
    )
    result = executor.evaluate(rule, {"risk_score": 20})
    assert result is None


def test_rule_executor_disabled_rule():
    executor = RuleExecutor()
    rule = _make_rule(
        conditions=RuleCondition(field="risk_score", op="gt", value=0),
        action={"action": "approve"},
        enabled=False,
    )
    result = executor.evaluate(rule, {"risk_score": 100})
    assert result is None


def test_rule_executor_nested_and():
    executor = RuleExecutor()
    rule = _make_rule(
        conditions=RuleCondition(
            field="",
            op="",
            value=None,
            logic="AND",
            items=[
                RuleCondition(field="risk_score", op="gt", value=50),
                RuleCondition(field="supplier_rating", op="lt", value=3.0),
            ],
        ),
        action={"action": "reject"},
    )
    # 两个条件都满足 → 命中
    assert executor.evaluate(rule, {"risk_score": 80, "supplier_rating": 2.0}) is not None
    # 只满足一个 → 不命中
    assert executor.evaluate(rule, {"risk_score": 80, "supplier_rating": 4.0}) is None


def test_rule_executor_nested_or():
    executor = RuleExecutor()
    rule = _make_rule(
        conditions=RuleCondition(
            field="",
            op="",
            value=None,
            logic="OR",
            items=[
                RuleCondition(field="delay_days", op="gt", value=10),
                RuleCondition(field="price_deviation", op="gt", value=20),
            ],
        ),
        action={"action": "escalate"},
    )
    assert executor.evaluate(rule, {"delay_days": 15, "price_deviation": 0}) is not None
    assert executor.evaluate(rule, {"delay_days": 1, "price_deviation": 50}) is not None


def test_rule_executor_nested_not():
    executor = RuleExecutor()
    rule = _make_rule(
        conditions=RuleCondition(
            field="",
            op="",
            value=None,
            logic="NOT",
            items=[RuleCondition(field="is_active", op="eq", value=True)],
        ),
        action={"action": "escalate"},
    )
    assert executor.evaluate(rule, {"is_active": False}) is not None
    assert executor.evaluate(rule, {"is_active": True}) is None


def test_rule_executor_action_interpolation():
    executor = RuleExecutor()
    rule = _make_rule(
        conditions=RuleCondition(field="risk_score", op="gt", value=50),
        action={"action": "escalate", "reason": "风险评分 {risk_score} 超标"},
    )
    result = executor.evaluate(rule, {"risk_score": 88})
    assert result["reason"] == "风险评分 88 超标"


def test_rule_executor_unknown_operator_returns_false():
    executor = RuleExecutor()
    rule = _make_rule(
        conditions=RuleCondition(field="risk_score", op="nonexistent_op", value=1),
        action={"action": "approve"},
    )
    assert executor.evaluate(rule, {"risk_score": 100}) is None


# ──────────────────────────────────────────────
# RulePrioritizer：优先级排序
# ──────────────────────────────────────────────

def test_rule_prioritizer_first_match_by_priority():
    rules = [
        _make_rule(rule_id="low", priority=1,
                   conditions=RuleCondition(field="x", op="gt", value=0),
                   action={"action": "approve"}),
        _make_rule(rule_id="high", priority=100,
                   conditions=RuleCondition(field="x", op="gt", value=0),
                   action={"action": "reject"}),
    ]
    prioritizer = RulePrioritizer(rules)
    result = prioritizer.execute({"x": 1})
    assert result["action"] == "reject"  # 高优先级规则先命中


def test_rule_prioritizer_no_match():
    rules = [
        _make_rule(rule_id="r1",
                   conditions=RuleCondition(field="x", op="gt", value=100),
                   action={"action": "reject"}),
    ]
    prioritizer = RulePrioritizer(rules)
    assert prioritizer.execute({"x": 1}) is None


# ──────────────────────────────────────────────
# DSLParser：解析
# ──────────────────────────────────────────────

def test_dsl_parser_parse_dict():
    data = {
        "rule_id": "r_risky",
        "rule_name": "高风险拒绝",
        "priority": 10,
        "enabled": True,
        "conditions": {
            "logic": "AND",
            "items": [
                {"field": "risk_score", "operator": "gt", "value": 70},
                {"field": "supplier_rating", "operator": "lt", "value": 3.0},
            ],
        },
        "action": {"action": "reject", "reason": "高风险供应商"},
    }
    rule = DSLParser.parse_dict(data)
    assert rule.rule_id == "r_risky"
    assert rule.rule_name == "高风险拒绝"
    assert rule.priority == 10
    assert rule.conditions is not None
    assert rule.conditions.logic == "AND"
    assert len(rule.conditions.items) == 2
    assert rule.action == {"action": "reject", "reason": "高风险供应商"}


def test_dsl_parser_parse_yaml():
    yaml_content = """
rule_id: r_yaml
rule_name: YAML规则
priority: 5
conditions:
  field: risk_score
  operator: gte
  value: 50
action:
  action: escalate
"""
    rule = DSLParser.parse_yaml(yaml_content)
    assert rule.rule_id == "r_yaml"
    assert rule.conditions.field == "risk_score"
    assert rule.conditions.op == "gte"
    assert rule.action["action"] == "escalate"


# ──────────────────────────────────────────────
# DecisionTreeWalker：_evaluate 与 walk
# ──────────────────────────────────────────────

def test_tree_walker_evaluate_operators():
    walker = DecisionTreeWalker()
    assert walker._evaluate({"field_name": "x", "operator": "gt", "threshold_value": 10}, {"x": 20}) is True
    assert walker._evaluate({"field_name": "x", "operator": "gt", "threshold_value": 10}, {"x": 5}) is False
    assert walker._evaluate({"field_name": "x", "operator": "lte", "threshold_value": 10}, {"x": 10}) is True
    assert walker._evaluate({"field_name": "x", "operator": "eq", "threshold_value": "a"}, {"x": "a"}) is True
    assert walker._evaluate({"field_name": "x", "operator": "in", "threshold_value": "abc"}, {"x": "b"}) is True


def test_tree_walker_evaluate_missing_field():
    walker = DecisionTreeWalker()
    # 字段不存在 → 返回 False
    assert walker._evaluate({"field_name": "nonexistent", "operator": "gt", "threshold_value": 1}, {}) is False


def test_tree_walker_evaluate_unknown_operator():
    walker = DecisionTreeWalker()
    assert walker._evaluate({"field_name": "x", "operator": "bogus", "threshold_value": 1}, {"x": 1}) is False


class _FakeRuleRepo:
    """模拟 RuleRepository，用于测试 walk 遍历逻辑。"""

    def __init__(self, node_map, children_map):
        self._node_map = node_map
        self._children_map = children_map

    async def get_by_id(self, node_id):
        return self._node_map.get(node_id)

    async def get_children(self, parent_id):
        return self._children_map.get(parent_id, [])


def _node(node_id, rule_type, **kwargs):
    """构造一个类 RuleNode 的 mock 对象（含 .value 枚举访问）。"""
    class _EnumVal:
        def __init__(self, value):
            self.value = value

    class _Node:
        def __init__(self, node_id, rule_type, **kwargs):
            self.id = node_id
            self.rule_type = _EnumVal(rule_type)
            self.action = kwargs.get("action")
            self.field_name = kwargs.get("field_name")
            self.operator = kwargs.get("operator")
            self.threshold_value = kwargs.get("threshold_value")
            self.logic_op = kwargs.get("logic_op")
            self.priority = kwargs.get("priority", 0)

    return _Node(node_id, rule_type, **kwargs)


def test_tree_walker_walk_action_node():
    """根节点即 action 节点，应直接命中。"""
    repo = _FakeRuleRepo(
        node_map={"root": _node("root", "action", action="approve")},
        children_map={},
    )
    walker = DecisionTreeWalker(rule_repo=repo)
    context = {"decision_action": None}
    path = asyncio.run(walker.walk("root", context))
    assert context["decision_action"] == "approve"
    assert path == ["root"]


def test_tree_walker_walk_condition_true_then_action():
    """条件为真 → 走到 action 节点。"""
    repo = _FakeRuleRepo(
        node_map={
            "cond": _node("cond", "condition", field_name="risk_score", operator="gt", threshold_value="50"),
            "act": _node("act", "action", action="reject"),
        },
        children_map={"cond": [_node("act", "action", action="reject")]},
    )
    walker = DecisionTreeWalker(rule_repo=repo)
    context = {"risk_score": 80, "decision_action": None}
    path = asyncio.run(walker.walk("cond", context))
    assert context["decision_action"] == "reject"
    assert path == ["cond", "act"]


def test_tree_walker_walk_condition_false_stops():
    """条件为假 → 应停止，不产出 action（修复后的核心行为）。"""
    repo = _FakeRuleRepo(
        node_map={
            "cond": _node("cond", "condition", field_name="risk_score", operator="gt", threshold_value="50"),
            "act": _node("act", "action", action="reject"),
        },
        children_map={"cond": [_node("act", "action", action="reject")]},
    )
    walker = DecisionTreeWalker(rule_repo=repo)
    context = {"risk_score": 10, "decision_action": None}
    path = asyncio.run(walker.walk("cond", context))
    # 条件为假，不应命中 action，也不应走到子节点
    assert context["decision_action"] is None
    assert path == ["cond"]


def test_tree_walker_walk_priority_sorted_children():
    """多子节点时应按 priority 降序取第一个。"""
    low = _node("child_low", "action", action="approve", priority=1)
    high = _node("child_high", "action", action="reject", priority=10)
    repo = _FakeRuleRepo(
        node_map={
            "root": _node("root", "condition", field_name="x", operator="gt", threshold_value="0"),
            "child_low": low,
            "child_high": high,
        },
        children_map={"root": [low, high]},
    )
    walker = DecisionTreeWalker(rule_repo=repo)
    context = {"x": 1, "decision_action": None}
    path = asyncio.run(walker.walk("root", context))
    # priority 高者先命中
    assert context["decision_action"] == "reject"
    assert path == ["root", "child_high"]
