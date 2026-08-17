"""AI 模块单元测试。

覆盖本次优化改动的核心逻辑，全部无需真实 DB / LLM / Ollama 服务：
- Mock LLM 修复（不再 StopIteration）
- 查询复杂度分析器
- 风险评分工具
- 决策矩阵兜底与置信度映射
- 规则工具降级路径
- AgentState 清理后的行为
- Prompt 加载器字段校验
"""

import asyncio
from itertools import repeat

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.agents.nodes.analyst_node import _apply_historical_adjustment, _score_to_level
from app.agents.nodes.decider_node import _confidence_for_action, _resolve_decision
from app.agents.state import (
    AgentState,
    DecisionStatus,
    RiskLevel,
    create_initial_state,
)
from app.agents.tools.risk_tools import calculate_risk_score
from app.core.model_selector import (
    ModelCategory,
    QueryComplexity,
    QueryComplexityAnalyzer,
)


# ──────────────────────────────────────────────
# P1-4: Mock LLM 修复
# ──────────────────────────────────────────────
def test_mock_llm_does_not_crash_on_invoke():
    """Mock 模型应能无限产出确定性回复，而非 StopIteration。"""
    model = GenericFakeChatModel(messages=iter(repeat(AIMessage(content="[mock] hi"))))
    # 连续调用多次，验证无限迭代器行为
    for _ in range(3):
        resp = model.invoke("hello")
        assert resp.content == "[mock] hi"


def test_get_llm_mock_mode():
    """get_llm(mock=True) 返回可 invoke 的 mock 模型。"""
    from app.core.llm import get_llm

    llm = get_llm(mock=True)
    resp = llm.invoke("test")
    assert isinstance(resp, AIMessage)
    assert resp.content  # 非空


# ──────────────────────────────────────────────
# 查询复杂度分析器
# ──────────────────────────────────────────────
def test_complexity_analyzer_simple():
    analyzer = QueryComplexityAnalyzer()
    score = analyzer.analyze("你好")
    assert score.level == QueryComplexity.SIMPLE
    assert 0.0 <= score.score <= 1.0


def test_complexity_analyzer_complex():
    analyzer = QueryComplexityAnalyzer()
    score = analyzer.analyze("如何设计多Agent分布式架构并实现异步并发优化")
    assert score.level == QueryComplexity.COMPLEX
    assert score.score >= 0.5


def test_complexity_analyzer_empty():
    analyzer = QueryComplexityAnalyzer()
    score = analyzer.analyze("")
    assert score.level == QueryComplexity.SIMPLE
    assert score.score == 0.0


# ──────────────────────────────────────────────
# 风险评分工具
# ──────────────────────────────────────────────
def test_calculate_risk_score_low():
    result = calculate_risk_score.invoke({
        "delay_days": 0,
        "price_deviation": 0,
        "supplier_rating": 5.0,
        "historical_incidents": 0,
    })
    assert result["level"] == "low"
    assert result["score"] == 0.0


def test_calculate_risk_score_critical_and_capped():
    result = calculate_risk_score.invoke({
        "delay_days": 10,
        "price_deviation": 20,
        "supplier_rating": 2,
        "historical_incidents": 1,
    })
    assert result["level"] == "critical"
    assert result["score"] == 100.0  # 已封顶


# ──────────────────────────────────────────────
# P2-7: 决策矩阵兜底
# ──────────────────────────────────────────────
def test_confidence_for_action():
    assert _confidence_for_action("approve", "low") == 0.95
    assert _confidence_for_action("approve", "high") == 0.80
    assert _confidence_for_action("escalate", "medium") == 0.60
    assert _confidence_for_action("reject", "critical") == 0.90


def test_resolve_decision_matrix_approve():
    """DB 不可达时优雅回退到矩阵（low 风险 → approve）。"""
    decision, confidence, path, source = asyncio.run(
        _resolve_decision("r1", 25.0, "low", {})
    )
    assert decision == "approve"
    assert confidence == 0.95
    assert path == ["root", "risk_assessment", "approve"]
    assert source == "matrix"


def test_resolve_decision_matrix_reject():
    """高评分 → reject。"""
    decision, confidence, path, source = asyncio.run(
        _resolve_decision("r2", 80.0, "critical", {})
    )
    assert decision == "reject"
    assert confidence == 0.90
    assert source == "matrix"


# ──────────────────────────────────────────────
# P3-10: AgentState 清理后行为
# ──────────────────────────────────────────────
def test_agent_state_init_and_attr_access():
    state = AgentState(request_id="r", raw_data_id="d")
    assert state.request_id == "r"
    assert state.status == DecisionStatus.PENDING
    assert state["anomaly_tags"] == []


def test_agent_state_missing_attr_raises():
    state = AgentState()
    with pytest.raises(AttributeError):
        _ = state.nonexistent_field


def test_create_initial_state():
    state = create_initial_state("r1", "d1")
    assert state["request_id"] == "r1"
    assert state["raw_data_id"] == "d1"
    assert state["status"] == DecisionStatus.PENDING
    assert state["retry_count"] == 0
    assert state["risk_score"] is None


# ──────────────────────────────────────────────
# P3-13: Prompt 加载器字段校验
# ──────────────────────────────────────────────
def test_prompt_loader_loads_valid_prompt():
    from app.agents.prompt_loader import get_prompt_loader

    prompt = asyncio.run(get_prompt_loader().get_prompt("analyst"))
    assert prompt.get("system_prompt")
    assert prompt.get("description")


def test_prompt_loader_missing_file_fallback():
    from app.agents.prompt_loader import PromptLoader

    loader = PromptLoader()
    prompt = asyncio.run(loader.get_prompt("nonexistent_agent", "v99"))
    # 文件不存在时返回兜底字段
    assert "system_prompt" in prompt
    assert "description" in prompt


# ──────────────────────────────────────────────
# P0: 模型类别枚举（StrEnum 兼容性）
# ──────────────────────────────────────────────
def test_model_category_strenum():
    assert ModelCategory.SMALL.value == "small"
    assert ModelCategory.LARGE.value == "large"
    # StrEnum 是 str 子类
    assert isinstance(ModelCategory.SMALL, str)


def test_risk_level_strenum():
    assert RiskLevel.HIGH.value == "high"
    assert isinstance(RiskLevel.CRITICAL, str)


# ──────────────────────────────────────────────
# P0-3: query_historical_patterns 降级（无 DB）
# ──────────────────────────────────────────────
def test_query_historical_patterns_degrades_without_db():
    from app.agents.tools.risk_tools import query_historical_patterns

    result = query_historical_patterns.invoke({"entity_id": "supplier_1"})
    # 无 DB 时应优雅返回空结构，而非抛出异常
    assert result["entity_id"] == "supplier_1"
    assert result["similarity_score"] == 0.0
    assert isinstance(result["patterns"], list)


# ──────────────────────────────────────────────
# A1: 历史模式评分调整
# ──────────────────────────────────────────────
def test_historical_adjustment_no_history():
    """无历史模式时评分不变。"""
    score, level = _apply_historical_adjustment(
        raw_score=40.0, similarity_score=0.0, historical_pattern_count=0
    )
    assert score == 40.0
    assert level == "medium"


def test_historical_adjustment_upscores_risk():
    """有历史高风险记录时评分上调，且可能提升等级。"""
    score, level = _apply_historical_adjustment(
        raw_score=45.0, similarity_score=0.5, historical_pattern_count=3
    )
    # 45 + 0.5*20 = 55 → 从 medium 提升到 high
    assert score == 55.0
    assert level == "high"


def test_historical_adjustment_capped_at_100():
    score, level = _apply_historical_adjustment(
        raw_score=95.0, similarity_score=1.0, historical_pattern_count=5
    )
    assert score == 100.0
    assert level == "critical"


def test_historical_adjustment_similarity_clamped():
    """相似度越界时被钳制在 [0,1]。"""
    score, _ = _apply_historical_adjustment(
        raw_score=50.0, similarity_score=2.0, historical_pattern_count=1
    )
    # 2.0 被钳制为 1.0 → 50 + 20 = 70
    assert score == 70.0


def test_score_to_level_boundaries():
    assert _score_to_level(30) == "low"
    assert _score_to_level(31) == "medium"
    assert _score_to_level(50) == "medium"
    assert _score_to_level(51) == "high"
    assert _score_to_level(70) == "high"
    assert _score_to_level(71) == "critical"

