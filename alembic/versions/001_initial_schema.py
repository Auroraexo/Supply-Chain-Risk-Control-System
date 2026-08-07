"""Alembic 迁移脚本模板。"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库。"""
    # 原始数据表
    op.create_table(
        "raw_data",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("data_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.Enum("pending", "processed", "invalid", name="rawdatastatus"), default="pending"),
        sa.Column("quality_score", sa.Float, default=None),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime, default=None),
        sa.Index("idx_source", "source_type", "source_id"),
        sa.Index("idx_status", "status"),
        sa.Index("idx_created", "created_at"),
    )

    # 分析结果表
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False, index=True),
        sa.Column("raw_data_id", sa.String(36), sa.ForeignKey("raw_data.id"), nullable=False),
        sa.Column("risk_score", sa.Float, default=None),
        sa.Column("risk_level", sa.Enum("low", "medium", "high", "critical", name="risklevel"), default=None),
        sa.Column("anomaly_tags", sa.JSON, default=None),
        sa.Column("reasoning", sa.Text, default=None),
        sa.Column("facts_summary", sa.JSON, default=None),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, default=None),
    )

    # 决策结果表
    op.create_table(
        "decision_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False, index=True),
        sa.Column("analysis_id", sa.String(36), sa.ForeignKey("analysis_results.id"), nullable=False),
        sa.Column("decision", sa.Enum("approve", "reject", "escalate", "pending_review", name="decision"), nullable=False),
        sa.Column("confidence", sa.Float, default=None),
        sa.Column("explanation", sa.Text, default=None),
        sa.Column("decision_path", sa.JSON, default=None),
        sa.Column("reflection_passed", sa.Boolean, default=None),
        sa.Column("reviewed_by", sa.String(100), default=None),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, default=None),
    )

    # 规则节点表
    op.create_table(
        "rule_nodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("rule_nodes.id", ondelete="CASCADE"), default=None, index=True),
        sa.Column("rule_name", sa.String(200), nullable=False),
        sa.Column("rule_type", sa.Enum("condition", "action", "group", name="ruletype"), nullable=False),
        sa.Column("condition_type", sa.String(50), default=None),
        sa.Column("field_name", sa.String(100), default=None),
        sa.Column("operator", sa.String(20), default=None),
        sa.Column("threshold_value", sa.String(200), default=None),
        sa.Column("logic_op", sa.Enum("AND", "OR", "NOT", name="logicop"), default="AND"),
        sa.Column("weight", sa.Float, default=1.0),
        sa.Column("action", sa.String(50), default=None),
        sa.Column("action_params", sa.JSON, default=None),
        sa.Column("priority", sa.Integer, default=0),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("description", sa.String(500), default=None),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, default=None),
    )

    # 规则版本表
    op.create_table(
        "rule_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("rule_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("snapshot", sa.JSON, nullable=False),
        sa.Column("changed_by", sa.String(100), default=None),
        sa.Column("change_reason", sa.String(500), default=None),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, default=None),
        sa.UniqueConstraint("rule_id", "version", name="uk_rule_version"),
    )

    # Agent 执行日志表
    op.create_table(
        "agent_execution_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False, index=True),
        sa.Column("agent_name", sa.String(50), nullable=False, index=True),
        sa.Column("node_name", sa.String(50), nullable=False),
        sa.Column("input_state", sa.JSON, default=None),
        sa.Column("output_state", sa.JSON, default=None),
        sa.Column("llm_model", sa.String(100), default=None),
        sa.Column("prompt_tokens", sa.Integer, default=0),
        sa.Column("completion_tokens", sa.Integer, default=0),
        sa.Column("latency_ms", sa.Integer, default=None),
        sa.Column("error_message", sa.Text, default=None),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, default=None),
    )


def downgrade() -> None:
    """降级数据库。"""
    op.drop_table("agent_execution_logs")
    op.drop_table("rule_versions")
    op.drop_table("rule_nodes")
    op.drop_table("decision_results")
    op.drop_table("analysis_results")
    op.drop_table("raw_data")
    # 删除枚举类型
    op.execute("DROP TYPE IF EXISTS decision")
    op.execute("DROP TYPE IF EXISTS risklevel")
    op.execute("DROP TYPE IF EXISTS rawdatastatus")
    op.execute("DROP TYPE IF EXISTS ruletype")
    op.execute("DROP TYPE IF EXISTS logicop")