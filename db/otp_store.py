"""
db/otp_store.py
SQLite-backed OTP storage with 5-minute TTL.

Mirrors the same pattern as db/sessions.py so there is a single SQLite file
(data/sessions.db) that holds both ussd_sessions and otp_tokens tables.

Schema
------
    otp_tokens (
        phone      TEXT PRIMARY KEY,
        hash       TEXT NOT NULL,      -- sha256(otp) hex digest
        expires    REAL NOT NULL,      -- Unix timestamp
        attempts   INTEGER NOT NULL DEFAULT 0
    )

TTL
---
    Rows expire after OTP_EXPIRES_SECONDS (default 300 s / 5 min).
    Expired rows are deleted lazily on lookup and eagerly by purge_expired().
"""

from __future__ import annotations

import sqlite3
import time

from core.config import settings

# Reuse the same DB file as ussd_sessions
DB_PATH = settings.DATA_DIR / "sessions.db"

MAX_ATTEMPTS = 5


# ── Connection ────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Init ──────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Creates the otp_tokens table if it doesn't already exist."""
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS otp_tokens (
                phone    TEXT    PRIMARY KEY,
                hash     TEXT    NOT NULL,
                expires  REAL    NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0
            )
            """
        )


# ── Write ─────────────────────────────────────────────────────────────────────

def store_otp(phone: str, otp_hash: str) -> None:
    """
    Persists a new OTP record, replacing any existing record for this phone.
    TTL is set from settings.OTP_EXPIRES_SECONDS (default 300 s).
    """
    expires = time.time() + settings.OTP_EXPIRES_SECONDS
    try:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO otp_tokens (phone, hash, expires, attempts)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(phone) DO UPDATE SET
                    hash     = excluded.hash,
                    expires  = excluded.expires,
                    attempts = 0
                """,
                (phone, otp_hash, expires),
            )
            conn.commit()
    except Exception as exc:
        print(f"[otp_store] store_otp({phone}) failed: {exc}")


# ── Read ──────────────────────────────────────────────────────────────────────

def get_otp(phone: str) -> dict | None:
    """
    Returns the OTP record for a phone number, or None if not found / expired.

    The record dict has keys: hash, expires, attempts.
    Expired records are deleted on read (lazy TTL).
    """
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT hash, expires, attempts FROM otp_tokens WHERE phone = ?",
                (phone,),
            ).fetchone()

        if not row:
            return None

        if time.time() > row["expires"]:
            delete_otp(phone)
            return None

        return {
            "hash":     row["hash"],
            "expires":  row["expires"],
            "attempts": row["attempts"],
        }
    except Exception as exc:
        print(f"[otp_store] get_otp({phone}) failed: {exc}")
        return None


# ── Increment attempts ────────────────────────────────────────────────────────

def increment_attempts(phone: str) -> int:
    """
    Increments the failed-attempt counter for a phone.
    Returns the new attempt count, or MAX_ATTEMPTS if the record is missing.
    """
    try:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE otp_tokens SET attempts = attempts + 1 WHERE phone = ?",
                (phone,),
            )
            conn.commit()
            row = conn.execute(
                "SELECT attempts FROM otp_tokens WHERE phone = ?",
                (phone,),
            ).fetchone()
            return row["attempts"] if row else MAX_ATTEMPTS
    except Exception as exc:
        print(f"[otp_store] increment_attempts({phone}) failed: {exc}")
        return MAX_ATTEMPTS


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_otp(phone: str) -> None:
    """Removes the OTP record for a phone (used on successful verify or expiry)."""
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM otp_tokens WHERE phone = ?", (phone,))
            conn.commit()
    except Exception as exc:
        print(f"[otp_store] delete_otp({phone}) failed: {exc}")


# ── Maintenance ───────────────────────────────────────────────────────────────

def purge_expired() -> None:
    """Removes all expired OTP records. Call at startup alongside sessions purge."""
    cutoff = time.time()
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM otp_tokens WHERE expires < ?", (cutoff,))
            conn.commit()
    except Exception as exc:
        print(f"[otp_store] purge_expired() failed: {exc}")
