from sqlalchemy.ext.asyncio import AsyncSession
from app.models.raw_data import RawData, RawDataStatus
from app.repositories.base import BaseRepository
from sqlalchemy import select

class RawDataRepository(BaseRepository[RawData]):
    def __init__(self, db: AsyncSession):
        super().__init__(RawData, db)

    async def get_by_hash(self, data_hash: str) -> RawData | None:
        result = await self.db.execute(select(RawData).where(RawData.data_hash == data_hash))
        return result.scalar_one_or_none()

    async def get_pending(self, limit: int = 10) -> list[RawData]:
        result = await self.db.execute(
            select(RawData).where(RawData.status == RawDataStatus.PENDING).limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(self, id: str, status: RawDataStatus, quality_score: float | None = None) -> RawData | None:
        values = {"status": status}
        from datetime import datetime
        if status == RawDataStatus.PROCESSED:
            values["processed_at"] = datetime.now()
        if quality_score is not None:
            values["quality_score"] = quality_score
        return await self.update(id, values)