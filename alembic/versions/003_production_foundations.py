"""Encrypted settings, immutable review events and risk treatment lifecycle.

Revision ID: 003
Revises: 24a1889aad53
"""

import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "24a1889aad53"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_notification_outbox_status", "notification_outbox", ["status"])
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "setting_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("key", "version", name="uq_setting_revision"),
    )
    op.create_index("ix_setting_revisions_key", "setting_revisions", ["key"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("before", sa.JSON()),
        sa.Column("after", sa.JSON()),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.add_column(
        "decision_results",
        sa.Column("case_status", sa.String(20), server_default="open", nullable=False),
    )
    op.add_column("decision_results", sa.Column("owner_id", sa.String(36)))
    op.add_column("decision_results", sa.Column("due_at", sa.DateTime()))
    op.add_column("decision_results", sa.Column("resolution", sa.Text()))
    op.add_column(
        "decision_results", sa.Column("revision", sa.Integer(), server_default="0", nullable=False)
    )
    op.create_foreign_key("fk_decision_owner", "decision_results", "users", ["owner_id"], ["id"])
    op.create_index(
        "ix_decision_results_case_status_due_at", "decision_results", ["case_status", "due_at"]
    )


def downgrade():
    op.drop_table("notification_outbox")
    op.drop_index("ix_decision_results_case_status_due_at", table_name="decision_results")
    op.drop_constraint("fk_decision_owner", "decision_results", type_="foreignkey")
    for name in ("revision", "resolution", "due_at", "owner_id", "case_status"):
        op.drop_column("decision_results", name)
    op.drop_table("audit_events")
    op.drop_table("setting_revisions")
    op.drop_table("system_settings")
