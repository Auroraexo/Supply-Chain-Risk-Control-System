"""规则匹配工具。"""
import asyncio
import concurrent.futures

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)


@tool
def match_rules(context: dict) -> dict:
    """根据上下文匹配决策规则。

    从 rule_nodes 活跃规则树中匹配第一个命中的 action。

    Args:
        context: 包含 risk_score, risk_level, supplier_rating 等字段的上下文
    """
    return _run_sync(lambda: _match_rules_async(context))


@tool
def get_decision_tree(root_node_id: str | None = None) -> dict:
    """获取决策树结构。

    Args:
        root_node_id: 根节点ID，为空则获取所有根节点
    """
    return _run_sync(lambda: _get_decision_tree_async(root_node_id))


def _run_sync(coro_factory):
    """在事件循环中安全地运行异步函数。

    coro_factory 是返回协程的零参数可调用对象，
    确保每次执行都新建协程（协程对象不可重复运行）。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro_factory())
        return future.result(timeout=10)


async def _match_rules_async(context: dict) -> dict:
    """异步匹配规则，返回命中的 action 与规则数量。"""
    try:
        from app.core.database import get_session_factory
        from app.repositories.rule_repo import RuleRepository
        from app.rule_engine.tree_walker import DecisionTreeWalker

        factory = get_session_factory()
        async with factory() as session:
            repo = RuleRepository(session)
            roots = await repo.get_root_nodes()

            if not roots:
                return {"matched_rules": [], "rule_count": 0, "context": context}

            walker = DecisionTreeWalker(rule_repo=repo)
            ctx = {**context, "decision_action": None}
            matched = []
            for root in roots:
                # 每次遍历前重置，避免读到上一个根节点的残留 action
                ctx["decision_action"] = None
                path = await walker.walk(root.id, ctx)
                action = ctx.get("decision_action")
                if action is not None:
                    matched.append({"root_id": root.id, "action": action, "path": path})
                    break

        return {
            "matched_rules": matched,
            "rule_count": len(roots),
            "context": context,
        }
    except Exception as e:
        logger.warning("rule_tools.match_rules_failed", error=str(e))
        return {"matched_rules": [], "rule_count": 0, "context": context, "error": str(e)}


async def _get_decision_tree_async(root_node_id: str | None) -> dict:
    """异步获取决策树结构。"""
    try:
        from app.core.database import get_session_factory
        from app.repositories.rule_repo import RuleRepository

        factory = get_session_factory()
        async with factory() as session:
            repo = RuleRepository(session)
            if root_node_id:
                node = await repo.get_by_id(root_node_id)
                if not node:
                    return {"root_node_id": root_node_id, "tree": {}, "found": False}
                return {
                    "root_node_id": root_node_id,
                    "tree": _node_to_dict(node),
                    "found": True,
                }

            roots = await repo.get_root_nodes()
            tree = {root.id: _node_to_dict(root) for root in roots}
            return {"root_node_id": None, "tree": tree, "root_count": len(roots)}
    except Exception as e:
        logger.warning("rule_tools.get_tree_failed", error=str(e))
        return {"root_node_id": root_node_id, "tree": {}, "error": str(e)}


def _node_to_dict(node) -> dict:
    """将 RuleNode 转换为可序列化的字典。"""
    return {
        "id": node.id,
        "rule_name": node.rule_name,
        "rule_type": node.rule_type.value if node.rule_type else None,
        "field_name": node.field_name,
        "operator": node.operator,
        "threshold_value": node.threshold_value,
        "action": node.action,
        "priority": node.priority,
        "is_active": node.is_active,
        "children": [_node_to_dict(c) for c in (node.children or [])],
    }
