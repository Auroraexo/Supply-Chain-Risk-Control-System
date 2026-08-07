"""Agent 共享状态定义。

使用 TypedDict 定义 LangGraph 全局状态，所有 Agent 节点通过此 State 通信。
"""

from typing import Annotated, Optional
from datetime import datetime
from enum import Enum

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    HUMAN_REVIEW = "human_review"
    FAILED = "failed"


class AgentState(dict):
    """Agent 全局状态（使用 dict 类型以兼容 LangGraph）。"""

    def __init__(self, **kwargs):
        defaults = {
            # 请求标识
            "request_id": "",
            "raw_data_id": "",
            # 侦察兵输出
            "structured_facts": None,
            "data_quality_score": None,
            "data_issues": [],
            # 分析师输出
            "risk_score": None,
            "risk_level": None,
            "anomaly_tags": [],
            "analysis_reasoning": None,
            # 决策官输出
            "decision_result": None,
            "confidence": None,
            "decision_explanation": None,
            "decision_path": [],
            # 自我反思输出
            "reflection_result": None,
            # 流程控制
            "status": DecisionStatus.PENDING,
            "retry_count": 0,
            "error_message": None,
            "messages": [],
            # 时间戳
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
        }
        defaults.update(kwargs)
        super().__init__(defaults)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"AgentState has no attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value


def create_initial_state(request_id: str, raw_data_id: str) -> dict:
    """创建初始状态。"""
    return {
        "request_id": request_id,
        "raw_data_id": raw_data_id,
        "status": DecisionStatus.PENDING,
        "retry_count": 0,
        "error_message": None,
        "structured_facts": None,
        "data_quality_score": None,
        "data_issues": [],
        "risk_score": None,
        "risk_level": None,
        "anomaly_tags": [],
        "analysis_reasoning": None,
        "decision_result": None,
        "confidence": None,
        "decision_explanation": None,
        "decision_path": [],
        "reflection_result": None,
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "completed_at": None,
    }