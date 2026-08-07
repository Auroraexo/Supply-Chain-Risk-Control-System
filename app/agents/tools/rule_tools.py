"""规则匹配工具。"""
from langchain_core.tools import tool


@tool
def match_rules(context: dict) -> dict:
    """根据上下文匹配决策规则。

    Args:
        context: 包含 risk_score, risk_level, supplier_rating 等字段的上下文
    """
    return {"matched_rules": [], "rule_count": 0, "context": context}


@tool
def get_decision_tree(root_node_id: str | None = None) -> dict:
    """获取决策树结构。

    Args:
        root_node_id: 根节点ID，为空则获取所有根节点
    """
    return {"root_node_id": root_node_id, "tree": {}}