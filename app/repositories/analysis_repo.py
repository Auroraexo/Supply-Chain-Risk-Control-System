from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_result import AnalysisResult, RiskLevel
from app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[AnalysisResult]):
    def __init__(self, db: AsyncSession):
        super().__init__(AnalysisResult, db)

    async def get_by_request_id(self, request_id: str) -> AnalysisResult | None:
        result = await self.db.execute(select(AnalysisResult).where(AnalysisResult.request_id == request_id))
        return result.scalar_one_or_none()

    async def get_by_raw_data_id(self, raw_data_id: str) -> list[AnalysisResult]:
        result = await self.db.execute(
            select(AnalysisResult).where(AnalysisResult.raw_data_id == raw_data_id).order_by(AnalysisResult.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_high_risk(self, limit: int = 20) -> list[AnalysisResult]:
        result = await self.db.execute(
            select(AnalysisResult).where(
                AnalysisResult.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
            ).order_by(AnalysisResult.risk_score.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 20) -> list[AnalysisResult]:
        result = await self.db.execute(
            select(AnalysisResult)
            .where(AnalysisResult.risk_level.isnot(None))
            .order_by(AnalysisResult.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
