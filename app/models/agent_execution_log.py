import uuid
from sqlalchemy import String, JSON, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class AgentExecutionLog(Base, TimestampMixin):
    __tablename__ = "agent_execution_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(50), nullable=False)
    input_state: Mapped[dict | None] = mapped_column(JSON, default=None)
    output_state: Mapped[dict | None] = mapped_column(JSON, default=None)
    llm_model: Mapped[str | None] = mapped_column(String(100), default=None)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)