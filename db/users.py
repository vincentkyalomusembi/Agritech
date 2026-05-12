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
