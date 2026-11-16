"""
Database module for RehabAI.
Provides SQLAlchemy models and session management for exercise sessions, users, and analytics.
"""
import os
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def _run_legacy_migration(connection):
    """
    Run legacy SQLite migration to add missing columns.
    This preserves historical installations that may have used older schema versions.
    """
    existing = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(exercise_sessions)")}
    columns_to_add = {
        "target_reps": "INTEGER",
        "pain_before": "INTEGER CHECK(pain_before >= 0 AND pain_before <= 10)",
        "pain_after": "INTEGER CHECK(pain_after >= 0 AND pain_after <= 10)",
        "recommendation": "VARCHAR(1000)",
        "status": "VARCHAR DEFAULT 'IN_PROGRESS'",
        "user_id": "VARCHAR(36)",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    }
    for name, definition in columns_to_add.items():
        if name not in existing:
            connection.exec_driver_sql(f"ALTER TABLE exercise_sessions ADD COLUMN {name} {definition}")

    # Create indexes for performance
    indexes = [
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_sessions_session_uuid ON exercise_sessions(session_uuid)",
        "CREATE INDEX IF NOT EXISTS ix_sessions_exercise_id ON exercise_sessions(exercise_id)",
        "CREATE INDEX IF NOT EXISTS ix_sessions_start_time ON exercise_sessions(start_time)",
    ]
    for idx_sql in indexes:
        try:
            connection.exec_driver_sql(idx_sql)
        except Exception:
            pass  # Index may already exist


if DATABASE_URL:
    engine_kwargs = {"pool_pre_ping": True}
    if DATABASE_URL.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, **engine_kwargs)
else:
    DB_PATH = os.path.abspath(os.environ.get("REHABAI_DB_PATH", os.path.join(DEFAULT_DB_DIR, "rehabai_sessions.db")))
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=new_uuid)
    email = Column(String(320), unique=True, index=True, nullable=False)
    full_name = Column(String(160), nullable=False)
    phone = Column(String(32), nullable=True)
    bio = Column(String(300), nullable=True)
    avatar_data_url = Column(Text, nullable=True)
    weekly_goal = Column(Integer, nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(16), default="patient", nullable=False)  # admin | doctor | patient
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Prescription(Base):
    """Exercise assignment from a doctor to a patient (lượt = target_reps, lần/ngày = sessions_per_day)."""
    __tablename__ = "prescriptions"
    id = Column(String(36), primary_key=True, default=new_uuid)
    doctor_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    exercise_id = Column(Integer, nullable=False)
    exercise_name = Column(String(200), nullable=False)
    target_reps = Column(Integer, nullable=False)
    sessions_per_day = Column(Integer, nullable=False, default=1)
    note = Column(String(500), nullable=True)
    status = Column(String(16), default="ACTIVE", nullable=False)  # ACTIVE | COMPLETED | CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String(36), primary_key=True, default=new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(32), default="info", nullable=False)  # prescription_assigned | prescription_completed | prescription_cancelled | system
    title = Column(String(200), nullable=False)
    body = Column(String(600), nullable=True)
    payload = Column(JSON, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class DoctorSchedule(Base):
    """Working hours of a doctor per weekday (0=Chủ nhật … 6=Thứ 7, like JS getDay)."""
    __tablename__ = "doctor_schedules"
    id = Column(String(36), primary_key=True, default=new_uuid)
    doctor_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(String(5), nullable=False)  # "08:00"
    end_time = Column(String(5), nullable=False)    # "17:00"
    note = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ClinicInfo(Base):
    """Singleton row with the clinic's public information (RAG source of truth)."""
    __tablename__ = "clinic_info"
    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(160), nullable=False, default="RehabAI")
    address = Column(String(300), nullable=True)
    phone = Column(String(32), nullable=True)
    notes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class PainAssessment(Base):
    __tablename__ = "pain_assessments"
    id = Column(String(36), primary_key=True, default=new_uuid)
    session_uuid = Column(String(36), ForeignKey("exercise_sessions.session_uuid"), nullable=False, index=True)
    phase = Column(String(16), nullable=False)  # before / after
    pain_score = Column(Integer, nullable=False)
    note = Column(String(2000), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String(120), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    value = Column(String(2000), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class ExerciseSession(Base):
    __tablename__ = "exercise_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    exercise_id = Column(Integer, nullable=False)
    exercise_name = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    completion_score = Column(Float, nullable=True)
    target_reps = Column(Integer, nullable=True)
    pain_before = Column(Integer, nullable=True)
    pain_after = Column(Integer, nullable=True)
    recommendation = Column(String, nullable=True)
    status = Column(String, default="IN_PROGRESS")
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ExerciseType(Base):
    __tablename__ = "exercise_types"
    id = Column(String(36), primary_key=True, default=new_uuid)
    exercise_code = Column(Integer, unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MovementPrediction(Base):
    __tablename__ = "movement_predictions"
    id = Column(String(36), primary_key=True, default=new_uuid)
    session_uuid = Column(String(36), ForeignKey("exercise_sessions.session_uuid"), nullable=False, index=True)
    prediction = Column(String(80), nullable=False)
    confidence = Column(Float, nullable=True)
    movement_quality = Column(Float, nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MovementFeedback(Base):
    __tablename__ = "movement_feedback"
    id = Column(String(36), primary_key=True, default=new_uuid)
    session_uuid = Column(String(36), ForeignKey("exercise_sessions.session_uuid"), nullable=False, index=True)
    message = Column(String(1000), nullable=False)
    severity = Column(String(24), default="info", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SessionRepetition(Base):
    __tablename__ = "session_repetitions"
    id = Column(String(36), primary_key=True, default=new_uuid)
    session_uuid = Column(String(36), ForeignKey("exercise_sessions.session_uuid"), nullable=False, index=True)
    repetition_number = Column(Integer, nullable=False)
    movement_quality = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Report(Base):
    __tablename__ = "reports"
    id = Column(String(36), primary_key=True, default=new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    report_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String(36), primary_key=True, default=new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(120), nullable=False, index=True)
    resource_type = Column(String(80), nullable=False)
    resource_id = Column(String(120), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    id = Column(String(36), primary_key=True, default=new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(160), nullable=True)
    language = Column(String(8), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(String(36), primary_key=True, default=new_uuid)
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(String(4000), nullable=False)
    provider = Column(String(32), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class DeepBreathingSession(Base):
    """Derived, non-clinical results for the guided breathing exercise."""
    __tablename__ = "deep_breathing_sessions"
    id = Column(String(36), primary_key=True, default=new_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    protocol_version = Column(String(32), nullable=False, default="v1")
    config = Column(JSON, nullable=False)
    target_cycles = Column(Integer, nullable=False, default=6)
    completed_cycles = Column(Integer, nullable=False, default=0)
    interrupted_cycles = Column(Integer, nullable=False, default=0)
    tracking_quality = Column(String(32), nullable=False, default="UNAVAILABLE")
    tracking_coverage = Column(Float, nullable=True)
    session_status = Column(String(32), nullable=False, default="IN_PROGRESS")
    average_cycle_duration = Column(Float, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DeepBreathingEvent(Base):
    __tablename__ = "deep_breathing_events"
    id = Column(String(36), primary_key=True, default=new_uuid)
    session_id = Column(String(36), ForeignKey("deep_breathing_sessions.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(48), nullable=False)
    phase = Column(String(40), nullable=True)
    cycle_index = Column(Integer, nullable=True)
    elapsed_seconds = Column(Float, nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

if engine.dialect.name == "sqlite":
    # Preserve historical installations that used the legacy table name.
    with engine.begin() as connection:
        tables = {row[0] for row in connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")}
        if "sessions" in tables and "exercise_sessions" not in tables:
            connection.exec_driver_sql("ALTER TABLE sessions RENAME TO exercise_sessions")

if os.getenv("REHABAI_AUTO_CREATE_SCHEMA", "1").strip().lower() in {"1", "true", "yes"}:
    # Developer/test convenience only. Production runs Alembic before Uvicorn.
    Base.metadata.create_all(bind=engine)

# SQLite's create_all adds missing tables but not new columns to existing
# tables (e.g. users.role introduced with the admin/doctor feature set).
# Only patch hand-made legacy DBs: the patch must be skipped when Alembic owns
# the schema (an `alembic_version` table is present) — in that case migration
# 0007 adds the column and the import-time patch would race it on re-upgrade.
if engine.dialect.name == "sqlite":
    with engine.begin() as connection:
        tables = {row[0] for row in connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")}
        if "users" in tables and "alembic_version" not in tables:
            user_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(users)")}
            if "role" not in user_columns:
                connection.exec_driver_sql("ALTER TABLE users ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'patient'")

# SQLite's create_all does not add columns to an existing demo database.
# Keep the local deployment upgradeable without destroying session history.
# SQLite's create_all does not add columns to an existing demo database.
# Keep the local deployment upgradeable without destroying session history.
if engine.dialect.name == "sqlite" and os.getenv("REHABAI_LEGACY_SQLITE_UPGRADE", "0") == "1":
    with engine.begin() as connection:
        _run_legacy_migration(connection)


def ensure_default_admin() -> None:
    """Create the first administrator account and the clinic profile on startup.

    Admin credentials come from REHABAI_ADMIN_EMAIL / REHABAI_ADMIN_PASSWORD so
    the deployment controls them; a dev fallback keeps a fresh install usable.
    The clinic profile is seeded from the same env vars with sensible defaults.
    """
    import logging
    from backend.core.security import hash_password

    db = SessionLocal()
    try:
        # --- Default administrator ---
        exists = db.query(User).filter(User.role == "admin").count() > 0
        if not exists:
            email = os.getenv("REHABAI_ADMIN_EMAIL", "admin@rehabai.local").strip().lower()
            password = os.getenv("REHABAI_ADMIN_PASSWORD", "RehabAI@2026")
            email_used = db.query(User).filter(User.email == email).first()
            if email_used:
                email_used.role = "admin"
            else:
                user = User(email=email, full_name="Quản trị hệ thống", password_hash=hash_password(password), role="admin")
                db.add(user)
                db.flush()
                db.add(AuditEvent(user_id=user.id, action="admin.bootstrap", resource_type="user", resource_id=user.id,
                                  payload={"email": email}))
                logging.getLogger("rehabai.db").warning("Default admin account created. Change REHABAI_ADMIN_PASSWORD before deploying.")

        # --- Default clinic profile ---
        if db.query(ClinicInfo).count() == 0:
            clinic = ClinicInfo(
                id="clinic",
                name=os.getenv("REHABAI_CLINIC_NAME", "RehabAI"),
                address=os.getenv("REHABAI_CLINIC_ADDRESS", "cc Tecco Phù Liên, Phan Đình Phùng, Thái Nguyên"),
                phone=os.getenv("REHABAI_CLINIC_PHONE", "0978469616"),
                notes={"working_hours_default": "Thứ 2–Thứ 6: 08:00–17:00 (đặt lịch qua số điện thoại)"},
            )
            db.add(clinic)
            db.add(AuditEvent(user_id=None, action="clinic.bootstrap", resource_type="clinic", resource_id="clinic"))
            logging.getLogger("rehabai.db").info("Default clinic profile created.")

        db.commit()
    finally:
        db.close()

# SQLite's create_all does not add columns to an existing demo database.
# Keep the local deployment upgradeable without destroying session history.
# SQLite's create_all does not add columns to an existing demo database.
# Keep the local deployment upgradeable without destroying session history.
if engine.dialect.name == "sqlite" and os.getenv("REHABAI_LEGACY_SQLITE_UPGRADE", "0") == "1":
    with engine.begin() as connection:
        _run_legacy_migration(connection)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
