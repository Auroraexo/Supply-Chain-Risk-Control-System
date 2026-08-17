"""决策树遍历器。

递归遍历 rule_nodes 表构建的决策树，返回决策路径。
"""
import time

import structlog

logger = structlog.get_logger(__name__)


class DecisionTreeWalker:
    """决策树遍历器。

    递归遍历 rule_nodes 表构建的决策树，返回决策路径。
    """

    def __init__(self, rule_repo=None):
        self._rule_repo = rule_repo
        if rule_repo:
            logger.info("tree_walker.initialized", has_repo=True)
        else:
            logger.warning("tree_walker.initialized", has_repo=False)

    async def walk(self, root_node_id: str, context: dict) -> list[str]:
        """遍历决策树，返回决策路径。

        Args:
            root_node_id: 根节点ID
            context: 决策上下文（包含 risk_score 等字段）

        Returns:
            决策路径节点ID列表
        """
        flow_start = time.monotonic()
        path: list[str] = []
        visited: set[str] = set()
        max_depth = 50
        depth = 0

        logger.info(
            "tree_walker.walk_start",
            root_node_id=root_node_id,
            context_keys=list(context.keys()),
        )

        current_node = await self._get_node(root_node_id)

        while current_node and depth < max_depth:
            node_id = current_node.get("id", "")
            node_type = current_node.get("rule_type")

            if node_id in visited:
                logger.warning(
                    "tree_walker.cycle_detected",
                    node_id=node_id,
                    depth=depth,
                    path=path,
                )
                break

            path.append(node_id)
            visited.add(node_id)
            depth += 1

            logger.debug(
                "tree_walker.node_visited",
                node_id=node_id,
                node_type=node_type,
                depth=depth,
                field_name=current_node.get("field_name"),
                operator=current_node.get("operator"),
                threshold_value=current_node.get("threshold_value"),
            )

            if node_type == "action":
                action = current_node.get("action")
                context["decision_action"] = action
                logger.info(
                    "tree_walker.action_reached",
                    node_id=node_id,
                    action=action,
                    path_length=len(path),
                    depth=depth,
                )
                break

            if node_type == "condition":
                condition_result = self._evaluate(current_node, context)
                logger.info(
                    "tree_walker.condition_evaluated",
                    node_id=node_id,
                    field=current_node.get("field_name"),
                    operator=current_node.get("operator"),
                    expected=current_node.get("threshold_value"),
                    actual=context.get(current_node.get("field_name", "")),
                    result=condition_result,
                    depth=depth,
                )
                # 条件为假：该分支不命中，停止遍历（无 action 产出）
                if not condition_result:
                    logger.info(
                        "tree_walker.branch_not_taken",
                        node_id=node_id,
                        field=current_node.get("field_name"),
                        expected=current_node.get("threshold_value"),
                        actual=context.get(current_node.get("field_name", "")),
                        depth=depth,
                    )
                    break

            children = await self._get_children(node_id)
            if not children:
                logger.info(
                    "tree_walker.leaf_node",
                    node_id=node_id,
                    node_type=node_type,
                    depth=depth,
                )
                break

            # 按 priority 降序取最优子节点（而非盲目取第一个）
            children_sorted = sorted(children, key=lambda c: c.get("priority", 0), reverse=True)
            current_node = children_sorted[0]

        if depth >= max_depth:
            logger.error(
                "tree_walker.max_depth_exceeded",
                root_node_id=root_node_id,
                max_depth=max_depth,
                path=path,
            )

        total_elapsed = round((time.monotonic() - flow_start) * 1000, 1)
        logger.info(
            "tree_walker.walk_complete",
            root_node_id=root_node_id,
            path=path,
            path_length=len(path),
            depth=depth,
            decision_action=context.get("decision_action"),
            elapsed_ms=total_elapsed,
        )
        return path

    def _evaluate(self, node: dict, context: dict) -> bool:
        """评估单个条件节点。"""
        field_name = node.get("field_name", "")
        operator = node.get("operator", "eq")
        threshold = node.get("threshold_value")
        field_value = context.get(field_name)

        if field_value is None:
            logger.debug(
                "tree_walker.field_not_found",
                field_name=field_name,
                context_keys=list(context.keys()),
            )
            return False

        try:
            if operator == "gt":
                return float(field_value) > float(threshold)
            elif operator == "gte":
                return float(field_value) >= float(threshold)
            elif operator == "lt":
                return float(field_value) < float(threshold)
            elif operator == "lte":
                return float(field_value) <= float(threshold)
            elif operator == "eq":
                return str(field_value) == str(threshold)
            elif operator == "neq":
                return str(field_value) != str(threshold)
            elif operator == "in":
                return str(field_value) in str(threshold)
            else:
                logger.warning(
                    "tree_walker.unknown_operator",
                    operator=operator,
                    field_name=field_name,
                )
                return False
        except (TypeError, ValueError) as e:
            logger.warning(
                "tree_walker.eval_error",
                field_name=field_name,
                operator=operator,
                field_value=field_value,
                threshold=threshold,
                error=str(e),
            )
            return False

    async def _get_node(self, node_id: str) -> dict | None:
        """获取节点数据。"""
        t0 = time.monotonic()
        if self._rule_repo:
            node = await self._rule_repo.get_by_id(node_id)
            elapsed = round((time.monotonic() - t0) * 1000, 1)
            if node:
                result = {
                    "id": node.id,
                    "rule_type": node.rule_type.value if node.rule_type else None,
                    "action": node.action,
                    "field_name": node.field_name,
                    "operator": node.operator,
                    "threshold_value": node.threshold_value,
                    "logic_op": node.logic_op.value if node.logic_op else None,
                }
                logger.debug(
                    "tree_walker.node_fetched",
                    node_id=node_id,
                    rule_type=result["rule_type"],
                    elapsed_ms=elapsed,
                )
                return result
            else:
                logger.warning(
                    "tree_walker.node_not_found",
                    node_id=node_id,
                    elapsed_ms=elapsed,
                )
        return None

    async def _get_children(self, parent_id: str) -> list[dict]:
        """获取子节点。"""
        t0 = time.monotonic()
        if self._rule_repo:
            children = await self._rule_repo.get_children(parent_id)
            elapsed = round((time.monotonic() - t0) * 1000, 1)
            result = [
                {
                    "id": c.id,
                    "rule_type": c.rule_type.value if c.rule_type else None,
                    "action": c.action,
                    "field_name": c.field_name,
                    "operator": c.operator,
                    "threshold_value": c.threshold_value,
                    "logic_op": c.logic_op.value if c.logic_op else None,
                    "priority": c.priority,
                }
                for c in children
            ]
            logger.debug(
                "tree_walker.children_fetched",
                parent_id=parent_id,
                child_count=len(result),
                child_ids=[c["id"] for c in result],
                elapsed_ms=elapsed,
            )
            return result
        return []
