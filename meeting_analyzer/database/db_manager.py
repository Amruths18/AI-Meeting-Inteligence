"""
database/db_manager.py
Handles all SQLite database operations for the Meeting Analyzer application.
"""

import sqlite3
import hashlib
import os
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "meeting_analyzer.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """Create tables from schema and run any pending column migrations."""
    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()
    conn = _get_connection()
    conn.executescript(schema)
    conn.commit()

    # ── Safe column migrations (ALTER TABLE IF column missing) ──────────────
    _add_column_if_missing(conn, "tasks",        "live_meeting_id", "INTEGER REFERENCES live_meetings(id) ON DELETE CASCADE")
    _add_column_if_missing(conn, "live_meetings", "transcript",      "TEXT DEFAULT ''")
    _add_column_if_missing(conn, "live_meetings", "summary",         "TEXT DEFAULT ''")
    _add_column_if_missing(conn, "live_meetings", "ended_at",        "TEXT")
    _add_column_if_missing(conn, "live_meetings", "status",          "TEXT DEFAULT 'active'")
    _add_column_if_missing(conn, "live_meetings", "host_ip",         "TEXT")
    _add_column_if_missing(conn, "live_meetings", "port",            "INTEGER")

    conn.commit()
    conn.close()


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, col_def: str):
    """Add a column to a table only if it doesn't already exist."""
    try:
        existing = [
            row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        ]
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
            print(f"[Migration] Added column '{column}' to '{table}'")
    except sqlite3.OperationalError as e:
        print(f"[Migration] Skipped '{column}' on '{table}': {e}")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Auth ──────────────────────────────────────────────────────────────────────

def authenticate_user(username: str, password: str) -> dict | None:
    hashed = hash_password(password)
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, hashed)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Users ─────────────────────────────────────────────────────────────────────

def get_all_users() -> list[dict]:
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY full_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_employees() -> list[dict]:
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM users WHERE role = 'employee' ORDER BY full_name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username: str, password: str, full_name: str, role: str) -> bool:
    try:
        conn = _get_connection()
        conn.execute(
            "INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), full_name, role)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def delete_user(user_id: int):
    conn = _get_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


# ── Meetings (uploaded) ───────────────────────────────────────────────────────

def create_meeting(title: str, audio_path: str, uploaded_by: int) -> int:
    conn = _get_connection()
    cur = conn.execute(
        "INSERT INTO meetings (title, audio_path, uploaded_by, status) VALUES (?, ?, ?, 'pending')",
        (title, audio_path, uploaded_by)
    )
    meeting_id = cur.lastrowid
    conn.commit()
    conn.close()
    return meeting_id


def update_meeting_results(meeting_id: int, transcript: str, summary: str):
    conn = _get_connection()
    conn.execute(
        "UPDATE meetings SET transcript = ?, summary = ?, status = 'done' WHERE id = ?",
        (transcript, summary, meeting_id)
    )
    conn.commit()
    conn.close()


def update_meeting_status(meeting_id: int, status: str):
    conn = _get_connection()
    conn.execute("UPDATE meetings SET status = ? WHERE id = ?", (status, meeting_id))
    conn.commit()
    conn.close()


def get_all_meetings() -> list[dict]:
    conn = _get_connection()
    rows = conn.execute("""
        SELECT m.*, u.full_name AS uploaded_by_name
        FROM meetings m
        LEFT JOIN users u ON m.uploaded_by = u.id
        ORDER BY m.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_meeting(meeting_id: int) -> dict | None:
    conn = _get_connection()
    row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_meeting(meeting_id: int):
    conn = _get_connection()
    conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    conn.commit()
    conn.close()


# ── Live Meetings ─────────────────────────────────────────────────────────────

def create_live_meeting(title: str, host_id: int, host_ip: str, port: int) -> int:
    conn = _get_connection()
    cur = conn.execute(
        "INSERT INTO live_meetings (title, host_id, host_ip, port) VALUES (?, ?, ?, ?)",
        (title, host_id, host_ip, port)
    )
    live_id = cur.lastrowid
    conn.commit()
    conn.close()
    return live_id


def end_live_meeting(live_meeting_id: int, transcript: str, summary: str):
    conn = _get_connection()
    conn.execute("""
        UPDATE live_meetings
        SET status = 'ended', transcript = ?, summary = ?, ended_at = datetime('now')
        WHERE id = ?
    """, (transcript, summary, live_meeting_id))
    conn.commit()
    conn.close()


def append_live_transcript(live_meeting_id: int, new_text: str):
    conn = _get_connection()
    conn.execute("""
        UPDATE live_meetings
        SET transcript = transcript || ? || char(10)
        WHERE id = ?
    """, (new_text, live_meeting_id))
    conn.commit()
    conn.close()


def get_live_meeting(live_meeting_id: int) -> dict | None:
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM live_meetings WHERE id = ?", (live_meeting_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_live_meetings() -> list[dict]:
    conn = _get_connection()
    rows = conn.execute("""
        SELECT lm.*, u.full_name AS host_name
        FROM live_meetings lm
        LEFT JOIN users u ON lm.host_id = u.id
        ORDER BY lm.started_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_participant(live_meeting_id: int, user_id: int):
    conn = _get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO live_participants (live_meeting_id, user_id) VALUES (?, ?)",
        (live_meeting_id, user_id)
    )
    conn.commit()
    conn.close()


def remove_participant(live_meeting_id: int, user_id: int):
    conn = _get_connection()
    conn.execute("""
        UPDATE live_participants SET left_at = datetime('now')
        WHERE live_meeting_id = ? AND user_id = ? AND left_at IS NULL
    """, (live_meeting_id, user_id))
    conn.commit()
    conn.close()


# ── Tasks ─────────────────────────────────────────────────────────────────────

def create_task(meeting_id: int | None, title: str, description: str,
                assigned_to: int | None, deadline: str | None,
                live_meeting_id: int | None = None) -> int:
    conn = _get_connection()
    cur = conn.execute(
        """INSERT INTO tasks (meeting_id, live_meeting_id, title, description, assigned_to, deadline)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (meeting_id, live_meeting_id, title, description, assigned_to, deadline)
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return task_id


def get_tasks_for_meeting(meeting_id: int) -> list[dict]:
    conn = _get_connection()
    rows = conn.execute("""
        SELECT t.*, u.full_name AS assigned_to_name
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.meeting_id = ?
        ORDER BY t.created_at
    """, (meeting_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tasks_for_live_meeting(live_meeting_id: int) -> list[dict]:
    conn = _get_connection()
    rows = conn.execute("""
        SELECT t.*, u.full_name AS assigned_to_name
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.live_meeting_id = ?
        ORDER BY t.created_at
    """, (live_meeting_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tasks_for_user(user_id: int) -> list[dict]:
    conn = _get_connection()
    rows = conn.execute("""
        SELECT t.*,
               COALESCE(m.title, lm.title) AS meeting_title,
               u.full_name AS assigned_to_name,
               CASE WHEN t.live_meeting_id IS NOT NULL THEN 'live' ELSE 'recorded' END AS source
        FROM tasks t
        LEFT JOIN meetings m ON t.meeting_id = m.id
        LEFT JOIN live_meetings lm ON t.live_meeting_id = lm.id
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.assigned_to = ?
        ORDER BY t.status, t.deadline
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_tasks() -> list[dict]:
    conn = _get_connection()
    rows = conn.execute("""
        SELECT t.*,
               COALESCE(m.title, lm.title) AS meeting_title,
               u.full_name AS assigned_to_name,
               CASE WHEN t.live_meeting_id IS NOT NULL THEN '🔴 Live' ELSE '📁 Recorded' END AS source
        FROM tasks t
        LEFT JOIN meetings m ON t.meeting_id = m.id
        LEFT JOIN live_meetings lm ON t.live_meeting_id = lm.id
        LEFT JOIN users u ON t.assigned_to = u.id
        ORDER BY t.status, t.deadline
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_task_status(task_id: int, status: str):
    conn = _get_connection()
    conn.execute(
        "UPDATE tasks SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, task_id)
    )
    conn.commit()
    conn.close()


def update_task(task_id: int, title: str, description: str,
                assigned_to: int | None, deadline: str | None, status: str):
    conn = _get_connection()
    conn.execute(
        """UPDATE tasks
           SET title=?, description=?, assigned_to=?,
               deadline=?, status=?, updated_at=datetime('now')
           WHERE id=?""",
        (title, description, assigned_to, deadline, status, task_id)
    )
    conn.commit()
    conn.close()


def delete_task(task_id: int):
    conn = _get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()