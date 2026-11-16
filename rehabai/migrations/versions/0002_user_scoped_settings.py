"""add user ownership to settings for existing installations"""

from alembic import op
import sqlalchemy as sa

revision = "0002_user_scoped_settings"
down_revision = "0001_initial_platform"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("system_settings") as batch:
        batch.add_column(sa.Column("user_id", sa.String(36), nullable=True))
        batch.create_index("ix_system_settings_user_id", ["user_id"], unique=False)
        batch.create_foreign_key("fk_system_settings_user_id", "users", ["user_id"], ["id"])


def downgrade():
    with op.batch_alter_table("system_settings") as batch:
        batch.drop_constraint("fk_system_settings_user_id", type_="foreignkey")
        batch.drop_index("ix_system_settings_user_id")
        batch.drop_column("user_id")
