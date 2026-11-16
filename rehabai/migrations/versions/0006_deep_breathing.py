"""add isolated guided deep breathing sessions and derived events

Revision ID: 0006_deep_breathing
Revises: 0005_user_profile
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_deep_breathing"
down_revision = "0005_user_profile"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "deep_breathing_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("protocol_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("target_cycles", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("completed_cycles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interrupted_cycles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tracking_quality", sa.String(32), nullable=False, server_default="UNAVAILABLE"),
        sa.Column("tracking_coverage", sa.Float(), nullable=True),
        sa.Column("session_status", sa.String(32), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("average_cycle_duration", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_deep_breathing_sessions_user_id", "deep_breathing_sessions", ["user_id"])
    op.create_table(
        "deep_breathing_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("deep_breathing_sessions.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("phase", sa.String(40), nullable=True),
        sa.Column("cycle_index", sa.Integer(), nullable=True),
        sa.Column("elapsed_seconds", sa.Float(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_deep_breathing_events_session_id", "deep_breathing_events", ["session_id"])
    op.create_index("ix_deep_breathing_events_user_id", "deep_breathing_events", ["user_id"])
    op.create_index("ix_deep_breathing_events_created_at", "deep_breathing_events", ["created_at"])


def downgrade():
    op.drop_index("ix_deep_breathing_events_created_at", table_name="deep_breathing_events")
    op.drop_index("ix_deep_breathing_events_user_id", table_name="deep_breathing_events")
    op.drop_index("ix_deep_breathing_events_session_id", table_name="deep_breathing_events")
    op.drop_table("deep_breathing_events")
    op.drop_index("ix_deep_breathing_sessions_user_id", table_name="deep_breathing_sessions")
    op.drop_table("deep_breathing_sessions")
