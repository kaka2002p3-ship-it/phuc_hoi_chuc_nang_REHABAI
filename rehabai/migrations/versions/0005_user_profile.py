"""add editable user profile fields

Revision ID: 0005_user_profile
Revises: 0004_chat_conversations
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_user_profile"
down_revision = "0004_chat_conversations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("bio", sa.String(300), nullable=True))
    op.add_column("users", sa.Column("avatar_data_url", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("weekly_goal", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("weight_kg", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("users", "weight_kg")
    op.drop_column("users", "height_cm")
    op.drop_column("users", "weekly_goal")
    op.drop_column("users", "avatar_data_url")
    op.drop_column("users", "bio")
    op.drop_column("users", "phone")
