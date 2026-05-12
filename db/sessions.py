

import json
import sqlite3
import time
from pathlib import Path

from core.config import settings

# ── Config ────────────────────────────────────────────────────────────────────

SESSION_TTL_HOURS = 24
DB_PATH = settings.DATA_DIR / "sessions.db"


# ── Connection ────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    """
    Returns a SQLite connection to the sessions DB.
    Phase 1: replace this function body with a psycopg2/asyncpg connection
    and nothing else in this file needs to change.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Creates the sessions table if it doesn't exist.
    Called once at app startup from app.py lifespan.
    """
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ussd_sessions (
                phone_number TEXT PRIMARY KEY,
                data         TEXT NOT NULL,
                updated_at   REAL NOT NULL
            )
        """)
        conn.commit()


# ── Public API ────────────────────────────────────────────────────────────────

def get_session(phone_number: str) -> dict:
    """
    Returns the session dict for a phone number.
    Returns {} if no session exists or session has expired (TTL).
    Never raises — safe to call unconditionally in the USSD handler.
    """
    try:
        with _get_conn()s as conn:
            row = conn.execute(
                "SELECT data, updated_at FROM ussd_sessions WHERE phone_number = ?",
                (phone_number,),
            ).fetchone()

        if not row:
            return {}

        age_hours = (time.time() - row["updated_at"]) / 3600
        if age_hours > SESSION_TTL_HOURS:
            delete_session(phone_number)
            return {}

        return json.loads(row["data"])

    except Exception as e:
        print(f"[sessions] get_session error: {e}")
        return {}


def set_session(phone_number: str, data: dict) -> None:
    """
    Upserts the session dict for a phone number.
    Merges with any existing data so callers can update one field at a time.
    Never raises.
    """
    try:
        existing = get_session(phone_number)
        merged = {**existing, **data}

        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO ussd_sessions (phone_number, data, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(phone_number) DO UPDATE SET
                    data       = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (phone_number, json.dumps(merged), time.time()),
            )
            conn.commit()

    except Exception as e:
        print(f"[sessions] set_session error: {e}")


def delete_session(phone_number: str) -> None:
    """Removes the session for a phone number. Used on TTL expiry or logout."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "DELETE FROM ussd_sessions WHERE phone_number = ?",
                (phone_number,),
            )
            conn.commit()
    except Exception as e:
        print(f"[sessions] delete_session error: {e}")


def purge_expired() -> int:
    """
    Deletes all sessions older than SESSION_TTL_HOURS.
    Returns the number of rows deleted.
    Call this from a nightly cron or the startup lifespan to keep the DB lean.
    """
    cutoff = time.time() - (SESSION_TTL_HOURS * 3600)
    try:
        with _get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM ussd_sessions WHERE updated_at < ?",
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        print(f"[sessions] purge_expired error: {e}")
        return 0