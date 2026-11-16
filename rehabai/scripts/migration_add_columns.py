"""
Database Migration Script
Purpose: Add missing columns to exercise_sessions table
Columns: target_reps, pain_before, pain_after, recommendation
"""
import sqlite3
import os
from datetime import datetime

DEFAULT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "data", "rehabai_sessions.db"))
DB_PATH = os.environ.get("REHABAI_DB_PATH", DEFAULT_DB_PATH)

def migrate():
    """Run migration to add missing columns"""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        print("Migration will be applied when database is created")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current columns
    cursor.execute("PRAGMA table_info(exercise_sessions)")
    columns = [col[1] for col in cursor.fetchall()]

    # Columns to add
    new_columns = {
        'target_reps': 'INTEGER',
        'pain_before': 'INTEGER CHECK(pain_before >= 0 AND pain_before <= 10)',
        'pain_after': 'INTEGER CHECK(pain_after >= 0 AND pain_after <= 10)',
        'recommendation': 'VARCHAR(1000)',
        'status': "VARCHAR DEFAULT 'IN_PROGRESS'"
    }

    added = []
    for col, dtype in new_columns.items():
        if col not in columns:
            try:
                cursor.execute(f"ALTER TABLE exercise_sessions ADD COLUMN {col} {dtype}")
                added.append(col)
                print(f"Added column: {col}")
            except Exception as e:
                print(f"Could not add {col}: {e}")

    # Create indexes
    indexes = [
        ("ix_sessions_session_uuid", "CREATE UNIQUE INDEX IF NOT EXISTS ix_sessions_session_uuid ON exercise_sessions(session_uuid)"),
        ("ix_sessions_exercise_id", "CREATE INDEX IF NOT EXISTS ix_sessions_exercise_id ON exercise_sessions(exercise_id)"),
        ("ix_sessions_start_time", "CREATE INDEX IF NOT EXISTS ix_sessions_start_time ON exercise_sessions(start_time)")
    ]

    for idx_name, idx_sql in indexes:
        try:
            cursor.execute(idx_sql)
            print(f"Created index: {idx_name}")
        except Exception as e:
            print(f"Index {idx_name}: {e}")

    conn.commit()

    # Verify
    cursor.execute("PRAGMA table_info(exercise_sessions)")
    final_columns = [col[1] for col in cursor.fetchall()]
    print(f"\nFinal columns: {final_columns}")

    conn.close()
    print(f"\nMigration completed! Added: {added}")
    return added

if __name__ == "__main__":
    print(f"Running migration at {datetime.now()}")
    migrate()
