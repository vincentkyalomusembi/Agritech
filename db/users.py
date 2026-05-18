from __future__ import annotations

import logging
from typing import Any

from core.config import settings

log = logging.getLogger(__name__)

# 
# Supabase client (lazy singleton)
# 

_supabase = None


def _client():
    """Returns a lazily-initialised Supabase client."""
    global _supabase
    if _supabase is None:
        try:
            from supabase import create_client  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "supabase-py is not installed. "
                "Run: pip install supabase"
            ) from exc

        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env "
                "before using db.users."
            )
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    return _supabase


# 
# Helpers
# 

def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Normalise a Supabase row to the keys the rest of the app expects."""
    return {
        "id":         row.get("id"),
        "phone":      row.get("phone"),
        "name":       row.get("name"),
        "county":     row.get("county"),
        "farm_type":  row.get("farm_type"),
        "soil_type":  row.get("soil_type"),
        "onboarded":  row.get("onboarded", False),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


# 
# Public API
# 

def get_user(phone: str) -> dict | None:
    """
    Fetch a user by phone number.
    Returns None if the phone is not registered.
    """
    try:
        res = (
            _client()
            .table("users")
            .select("*")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        if res.data:
            return _row_to_dict(res.data[0])
        return None
    except Exception as exc:
        log.error("get_user(%s) failed: %s", phone, exc)
        return None


def upsert_user(phone: str, data: dict[str, Any]) -> dict:
    """
    Insert or update a user row.

    Only the keys present in `data` are written; other columns are left
    unchanged (achieved via Supabase UPSERT + ignoreDuplicates=False).

    Args:
        phone: E.164 phone number used as the unique key.
        data:  Partial dict of columns to set (name, county, farm_type, …).

    Returns:
        The fresh user row as a dict.
    """
    # Merge phone into the payload (required for the upsert key)
    payload = {**data, "phone": phone}

    # Strip any keys that don't belong to the users table
    _VALID_COLUMNS = {"phone", "name", "county", "farm_type", "soil_type", "onboarded"}
    payload = {k: v for k, v in payload.items() if k in _VALID_COLUMNS}

    try:
        res = (
            _client()
            .table("users")
            .upsert(payload, on_conflict="phone")
            .execute()
        )
        if res.data:
            return _row_to_dict(res.data[0])
    except Exception as exc:
        log.error("upsert_user(%s) failed: %s", phone, exc)

    # Fallback: return whatever we have from a fresh GET
    return get_user(phone) or {"phone": phone, **data}


def get_or_create_user(phone: str) -> dict:
    """
    Returns an existing user or creates a bare skeleton row.
    Useful at the start of a USSD session to ensure a row exists.
    """
    user = get_user(phone)
    if user is None:
        user = upsert_user(phone, {"onboarded": False})
    return user


# ── Vets & Agri Officers ───────────────────────────────────────────────────────
# Seeded in db/schema.sql. Local SQLite fallback mirrors the Supabase schema.

import sqlite3 as _sqlite3
import time as _time_mod

_EXPERTS_DB = settings.DATA_DIR / "agritech.db"

_SEED_VETS = [
    ("+254700000004", "Dr. Sarah Ochieng",  "Kisumu",     "Nyanza"),
    ("+254700000005", "Dr. John Kamau",      "Kiambu",     "Central"),
    ("+254700000006", "Dr. Grace Wanjiru",   "Mombasa",    "Coast"),
    ("+254700000007", "Dr. Michael Otieno",  "Siaya",      "Nyanza"),
    ("+254700000008", "Dr. Faith Njeri",     "Nairobi",    "Nairobi"),
]

_SEED_AGRI = [
    ("+254700000009", "David Mutiso",      "Machakos",    "Eastern"),
    ("+254700000010", "Rebecca Chebet",    "Uasin Gishu", "Rift Valley"),
    ("+254700000011", "Samuel Kiplagat",   "Baringo",     "Rift Valley"),
    ("+254700000012", "Lucy Wambui",       "Murang'a",    "Central"),
    ("+254700000013", "Peter Kariuki",     "Kirinyaga",   "Central"),
]


def _expert_conn() -> _sqlite3.Connection:
    _EXPERTS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = _sqlite3.connect(_EXPERTS_DB)
    conn.row_factory = _sqlite3.Row
    return conn


def _init_expert_tables() -> None:
    now = _time_mod.time()
    with _expert_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS vets (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT    NOT NULL UNIQUE,
                name         TEXT    NOT NULL,
                county       TEXT    NOT NULL,
                region       TEXT,
                active       INTEGER NOT NULL DEFAULT 1,
                created_at   REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_vets_county ON vets (county);
            CREATE TABLE IF NOT EXISTS agri_officers (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT    NOT NULL UNIQUE,
                name         TEXT    NOT NULL,
                county       TEXT    NOT NULL,
                region       TEXT,
                active       INTEGER NOT NULL DEFAULT 1,
                created_at   REAL    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_agri_county ON agri_officers (county);
        """)
        conn.executemany(
            "INSERT OR IGNORE INTO vets (phone_number,name,county,region,created_at) VALUES (?,?,?,?,?)",
            [(p, n, c, r, now) for p, n, c, r in _SEED_VETS],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO agri_officers (phone_number,name,county,region,created_at) VALUES (?,?,?,?,?)",
            [(p, n, c, r, now) for p, n, c, r in _SEED_AGRI],
        )
        conn.commit()


def list_vets(county: str | None = None, limit: int = 3) -> list[dict]:
    """Returns active vets filtered by county (falls back to all if none in county)."""
    # ── Supabase ──────────────────────────────────────────────────────────────
    try:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            from supabase import create_client
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            q = client.table("vets").select("*").eq("active", True)
            if county:
                q = q.eq("county", county)
            res = q.limit(limit).execute()
            if res.data:
                return res.data
    except Exception:
        pass

    # ── Local SQLite ──────────────────────────────────────────────────────────
    _init_expert_tables()
    with _expert_conn() as conn:
        if county:
            rows = conn.execute(
                "SELECT * FROM vets WHERE active=1 AND county=? LIMIT ?", (county, limit)
            ).fetchall()
            if rows:
                return [dict(r) for r in rows]
        rows = conn.execute("SELECT * FROM vets WHERE active=1 LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def list_agri_officers(county: str | None = None, limit: int = 3) -> list[dict]:
    """Returns active agri officers filtered by county."""
    # ── Supabase ──────────────────────────────────────────────────────────────
    try:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            from supabase import create_client
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            q = client.table("agri_officers").select("*").eq("active", True)
            if county:
                q = q.eq("county", county)
            res = q.limit(limit).execute()
            if res.data:
                return res.data
    except Exception:
        pass

    # ── Local SQLite ──────────────────────────────────────────────────────────
    _init_expert_tables()
    with _expert_conn() as conn:
        if county:
            rows = conn.execute(
                "SELECT * FROM agri_officers WHERE active=1 AND county=? LIMIT ?", (county, limit)
            ).fetchall()
            if rows:
                return [dict(r) for r in rows]
        rows = conn.execute("SELECT * FROM agri_officers WHERE active=1 LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]