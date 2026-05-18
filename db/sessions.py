import json 
import sqlite3
import time
from pathlib import Path


from core.config import settings


#config
SESSION_TTL_HOURS = 24
DB_PATH = settings.DATA_DIR / "sessions.db"

#connection
def _get_conn() ->sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ussd_sessions (
            phone_number TEXT PRIMARY KEY,
            data         TEXT NOT NULL,
            updated_at   REAL NOT NULL
            )
            """
        )

def get_session(phone_number:str) -> dict:
    """Returns the session dict for a phone number """
    try:
        with _get_conn() as conn:
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
        print(f"Error getting session {phone_number}: {e}")
        return {}

def set_session(phone_number: str, data: dict) -> None:
    """
    Merges `data` into the existing session and persists it.

    Uses a read → merge → write pattern so that updating a single field
    (e.g. farm_type) never wipes other fields (e.g. county, name).
    """
    try:
        # 1. Read the current session (may be empty dict for new sessions)
        existing = get_session(phone_number)

        # 2. Merge: new data takes priority over old values
        merged = {**existing, **data}

        # 3. Write back the merged dict
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO ussd_sessions (phone_number, data, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(phone_number) DO UPDATE SET
                    data       = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (
                    phone_number,
                    json.dumps(merged),
                    time.time(),
                ),
            )
            conn.commit()
    except Exception as e:
        print(f"Error setting session for {phone_number}: {e}")


def delete_session(phone_number:str) -> None:
    """Removes a session"""
    try:
        with _get_conn() as conn:
            conn.execute(
                "DELETE FROM ussd_sessions WHERE phone_number = ?",
                (phone_number,),
            )
            conn.commit()
    except Exception as e:
        print(f"Error deleting session {phone_number}: {e}")

def purge_expired() -> None:
    """Removes all expired sessions in the background"""
    cutoff = time.time() - (SESSION_TTL_HOURS * 3600)
    try:
        with _get_conn() as conn:
            # This will be quick enough - no need for background threading for now
            conn.execute(
                "DELETE FROM ussd_sessions WHERE updated_at < ?",
                (cutoff,),
            )
            conn.commit()
    except Exception as e:
        # Don't crash the app if background cleanup fails
        print(f"Error purging expired sessions: {e}")
