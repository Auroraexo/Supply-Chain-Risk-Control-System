from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.agent_execution_log import AgentExecutionLog
from app.repositories.base import BaseRepository

class AgentLogRepository(BaseRepository[AgentExecutionLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(AgentExecutionLog, db)

    async def get_by_request_id(self, request_id: str) -> list[AgentExecutionLog]:
        result = await self.db.execute(
            select(AgentExecutionLog).where(AgentExecutionLog.request_id == request_id).order_by(AgentExecutionLog.created_at)
        )
        return list(result.scalars().all())

    async def get_total_tokens(self, request_id: str) -> int:
        result = await self.db.execute(
            select(func.sum(AgentExecutionLog.prompt_tokens + AgentExecutionLog.completion_tokens))
            .where(AgentExecutionLog.request_id == request_id)
        )
        return result.scalar() or 0