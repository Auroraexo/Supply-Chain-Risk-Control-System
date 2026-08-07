from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.decision_result import DecisionResult, Decision as DecisionEnum
from app.repositories.base import BaseRepository

class DecisionRepository(BaseRepository[DecisionResult]):
    def __init__(self, db: AsyncSession):
        super().__init__(DecisionResult, db)

    async def get_by_request_id(self, request_id: str) -> DecisionResult | None:
        result = await self.db.execute(select(DecisionResult).where(DecisionResult.request_id == request_id))
        return result.scalar_one_or_none()

    async def get_pending_reviews(self, limit: int = 20) -> list[DecisionResult]:
        result = await self.db.execute(
            select(DecisionResult).where(DecisionResult.decision == DecisionEnum.PENDING_REVIEW).limit(limit)
        )
        return list(result.scalars().all())