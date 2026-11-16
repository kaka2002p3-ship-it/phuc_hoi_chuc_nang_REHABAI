"""initial platform tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_platform"
down_revision = None
branch_labels = None
depends_on = None

def uuid_col():
    return sa.String(36)

def upgrade():
    op.create_table("users", sa.Column("id", uuid_col(), primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("full_name", sa.String(160), nullable=False), sa.Column("password_hash", sa.String(256), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("exercise_types", sa.Column("id", uuid_col(), primary_key=True), sa.Column("exercise_code", sa.Integer(), nullable=False, unique=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("exercise_sessions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("session_uuid", uuid_col(), nullable=False, unique=True), sa.Column("user_id", uuid_col()), sa.Column("exercise_id", sa.Integer(), nullable=False), sa.Column("exercise_name", sa.String(), nullable=False), sa.Column("start_time", sa.DateTime()), sa.Column("end_time", sa.DateTime()), sa.Column("completion_score", sa.Float()), sa.Column("target_reps", sa.Integer()), sa.Column("pain_before", sa.Integer()), sa.Column("pain_after", sa.Integer()), sa.Column("recommendation", sa.String()), sa.Column("status", sa.String()), sa.Column("metrics", sa.JSON()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["user_id"],["users.id"]))
    for name in ("pain_assessments", "movement_predictions", "movement_feedback", "session_repetitions"):
        if name == "pain_assessments": cols=[sa.Column("id",uuid_col(),primary_key=True),sa.Column("session_uuid",uuid_col(),nullable=False),sa.Column("phase",sa.String(16),nullable=False),sa.Column("pain_score",sa.Integer(),nullable=False),sa.Column("note",sa.String(2000)),sa.Column("timestamp",sa.DateTime(),nullable=False)]
        elif name == "movement_predictions": cols=[sa.Column("id",uuid_col(),primary_key=True),sa.Column("session_uuid",uuid_col(),nullable=False),sa.Column("prediction",sa.String(80),nullable=False),sa.Column("confidence",sa.Float()),sa.Column("movement_quality",sa.Float()),sa.Column("payload",sa.JSON()),sa.Column("created_at",sa.DateTime(),nullable=False)]
        elif name == "movement_feedback": cols=[sa.Column("id",uuid_col(),primary_key=True),sa.Column("session_uuid",uuid_col(),nullable=False),sa.Column("message",sa.String(1000),nullable=False),sa.Column("severity",sa.String(24),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False)]
        else: cols=[sa.Column("id",uuid_col(),primary_key=True),sa.Column("session_uuid",uuid_col(),nullable=False),sa.Column("repetition_number",sa.Integer(),nullable=False),sa.Column("movement_quality",sa.Float()),sa.Column("created_at",sa.DateTime(),nullable=False)]
        op.create_table(name, *cols, sa.ForeignKeyConstraint(["session_uuid"],["exercise_sessions.session_uuid"]))
    op.create_table("reports",sa.Column("id",uuid_col(),primary_key=True),sa.Column("user_id",uuid_col()),sa.Column("report_type",sa.String(50),nullable=False),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False),sa.ForeignKeyConstraint(["user_id"],["users.id"]))
    op.create_table("system_settings",sa.Column("key",sa.String(120),primary_key=True),sa.Column("value",sa.String(2000),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False))

def downgrade():
    for name in ("system_settings","reports","session_repetitions","movement_feedback","movement_predictions","pain_assessments","exercise_sessions","exercise_types","users"): op.drop_table(name)
