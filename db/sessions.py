
"""
db/sessions.py
Persistent USSD session store with TTL.
 
Why this exists
---------------
Africa's Talking sends the full navigation path in `text` (e.g. "1*2*1"),
so the USSD flow itself is stateless. BUT we still need a server-side store
for data that can't live in the menu path:
  - phone_number → county (so we can skip asking again on next dial)
  - phone_number → name, farm_type, soil_type (user profile pre-Supabase)
  - Onboarding state: has this number completed onboarding?
 
Storage strategy (progressive, swappable)
-----------------------------------------
  Phase 0 (now):    SQLite file — zero dependencies, survives restarts,
                    works on Render free tier without extra services.
  Phase 1 (Supabase): Replace _get_conn() with psycopg2/asyncpg.
                    The get/set/delete interface stays identical.
 
Schema
------
  ussd_sessions (
    phone_number  TEXT PRIMARY KEY,
    data          TEXT NOT NULL,    -- JSON blob
    updated_at    REAL NOT NULL     -- Unix timestamp
  )
 
TTL: sessions older than SESSION_TTL_HOURS are expired on read.
"""


import json
import sqlite3
import time
from pathlib import settings

from core.config import settings

#config
SESSION_TTL_HOURS = 24
DB_PATH = settings.DATA_DIR / "sessions.db"


#Connection

def _get_conn() -> sqlite3.Connection:
    # returns a sqlite connection to the sessions db
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() ->None:
    #creates the sessions table if it does not exist
    
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
        conn.commit()

#Public API
def get_session(phone_number: str) -> dict:
    #returns the session dict for a phone number

    try:
        with _get_conn as conn:
            row = conn.execute(
                "SELECT data, updated_at FROM ussd_sessions WHERE phone_number = ?",
                (phone_number,),
            ).fetchone()

            if not row:
                return {}

            age_hours =  (time.time() - row["updated_at"]) / 3600

            if age_hours > SESSION_TTL_HOURS:
                delete_session(phone_number)
                return {}

def set_session(phone_number: str, data: dict) -> None:
    """upserts the session dict for a phone number
        merges with the existing data so callers can update one field at a time
    """

    
