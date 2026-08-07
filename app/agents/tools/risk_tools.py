"""风险计算工具。"""
from langchain_core.tools import tool


@tool
def calculate_risk_score(delay_days: int, price_deviation: float, supplier_rating: float, historical_incidents: int) -> dict:
    """计算供应链风险评分。

    Args:
        delay_days: 延迟天数
        price_deviation: 价格偏差百分比
        supplier_rating: 供应商评分 (0-5)
        historical_incidents: 历史事故次数
    """
    score = delay_days * 5.0 + price_deviation * 3.0 + (5 - supplier_rating) * 4.0 + historical_incidents * 10.0
    score = min(score, 100.0)
    level = "low"
    if score > 70:
        level = "critical"
    elif score > 50:
        level = "high"
    elif score > 30:
        level = "medium"
    return {"score": round(score, 2), "level": level}


@tool
def query_historical_patterns(entity_id: str, pattern_type: str = "risk") -> dict:
    """查询历史风险模式。

    Args:
        entity_id: 实体ID
        pattern_type: 模式类型 (risk/supplier/logistics)
    """
    return {"patterns": [], "similarity_score": 0.0, "entity_id": entity_id}