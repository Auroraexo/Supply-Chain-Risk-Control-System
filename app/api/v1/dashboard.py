"""Dashboard 统计 API 路由。

提供仪表盘所需的汇总统计、趋势数据和告警信息。
"""

from fastapi import APIRouter
from sqlalchemy import text, func
from app.api.deps import DBSession
from app.schemas.common import DataResponse

router = APIRouter(prefix="/dashboard")


@router.get("/summary", response_model=DataResponse)
async def get_summary(db: DBSession):
    """获取仪表盘汇总统计数据。"""
    # 风险等级统计
    risk_stats = await db.execute(
        text("""
            SELECT
                COUNT(*) as total_risks,
                COALESCE(SUM(CASE WHEN risk_level = 'critical' THEN 1 ELSE 0 END), 0) as critical_count,
                COALESCE(SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END), 0) as high_count,
                COALESCE(SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END), 0) as medium_count,
                COALESCE(SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END), 0) as low_count
            FROM analysis_results
        """)
    )
    row = risk_stats.fetchone()

    # 待处理决策数
    pending = await db.execute(
        text("SELECT COUNT(*) FROM decision_results WHERE decision = 'escalate' OR decision = 'pending_review'")
    )
    pending_count = pending.fetchone()[0]

    # 活跃规则数
    active_rules = await db.execute(
        text("SELECT COUNT(*) FROM rule_nodes WHERE is_active = 1")
    )
    active_count = active_rules.fetchone()[0]

    return DataResponse(data={
        "total_risks": row[0] or 0,
        "critical_count": row[1] or 0,
        "high_count": row[2] or 0,
        "medium_count": row[3] or 0,
        "low_count": row[4] or 0,
        "pending_decisions": pending_count,
        "active_rules": active_count,
        "last_updated": None,
    })


@router.get("/trends", response_model=DataResponse)
async def get_trends(db: DBSession, days: int = 7):
    """获取风险趋势数据（最近 N 天）。"""
    trends = await db.execute(
        text("""
            SELECT
                DATE(created_at) as date,
                COALESCE(SUM(CASE WHEN risk_level = 'critical' THEN 1 ELSE 0 END), 0) as critical,
                COALESCE(SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END), 0) as high,
                COALESCE(SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END), 0) as medium,
                COALESCE(SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END), 0) as low
            FROM analysis_results
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """),
        {"days": days}
    )
    data = [
        {"date": str(row[0]), "critical": row[1], "high": row[2], "medium": row[3], "low": row[4]}
        for row in trends.fetchall()
    ]
    return DataResponse(data=data)


@router.get("/alerts", response_model=DataResponse)
async def get_alerts(db: DBSession, limit: int = 10):
    """获取最新告警列表。"""
    alerts = await db.execute(
        text("""
            SELECT ar.id, ar.risk_level, ar.anomaly_tags, ar.created_at, rd.source_type
            FROM analysis_results ar
            LEFT JOIN raw_data rd ON ar.raw_data_id = rd.id
            WHERE ar.risk_level IN ('critical', 'high')
            ORDER BY ar.created_at DESC
            LIMIT :limit
        """),
        {"limit": limit}
    )
    data = [
        {
            "id": str(row[0]),
            "type": row[1] or "medium",
            "title": f"风险等级: {row[1]}",
            "description": f"来源: {row[4] or '未知'}, 异常标签: {row[2]}",
            "created_at": str(row[3]) if row[3] else None,
        }
        for row in alerts.fetchall()
    ]
    return DataResponse(data=data)