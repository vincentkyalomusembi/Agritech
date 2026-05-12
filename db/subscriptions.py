from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.config import settings

log = logging.getLogger(__name__)

# Supabase client (reuses the same singleton pattern as db/users.py)

_supabase = None


def _client():
    global _supabase
    if _supabase is None:
        try:
            from supabase import create_client  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "supabase-py is not installed. Run: pip install supabase"
            ) from exc

        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env."
            )
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    return _supabase


# Helpers

def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id":         row.get("id"),
        "user_id":    row.get("user_id"),
        "plan":       row.get("plan", "free"),
        "status":     row.get("status", "active"),
        "created_at": row.get("created_at"),
        "expires_at": row.get("expires_at"),
    }


def _is_expired(row: dict[str, Any]) -> bool:
    """True if expires_at is in the past."""
    raw = row.get("expires_at")
    if not raw:
        return False
    try:
        exp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return exp < datetime.now(timezone.utc)
    except (ValueError, AttributeError):
        return False


# Public API

def get_subscription(user_id: str) -> dict | None:
    """
    Returns the most recent subscription row for a user_id.
    Returns None if no subscription exists.
    """
    try:
        res = (
            _client()
            .table("subscriptions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return _row_to_dict(res.data[0])
        return None
    except Exception as exc:
        log.error("get_subscription(%s) failed: %s", user_id, exc)
        return None


def create_subscription(user_id: str, plan: str = "free") -> dict:
    """
    Creates a new subscription for the user.
    Raises ValueError for unknown plan names.
    """
    valid_plans = {"free", "basic", "pro"}
    if plan not in valid_plans:
        raise ValueError(f"Unknown plan '{plan}'. Choose from {valid_plans}.")

    payload = {
        "user_id": user_id,
        "plan":    plan,
        "status":  "active",
    }

    try:
        res = _client().table("subscriptions").insert(payload).execute()
        if res.data:
            return _row_to_dict(res.data[0])
    except Exception as exc:
        log.error("create_subscription(%s, %s) failed: %s", user_id, plan, exc)

    return {**payload, "id": None, "created_at": None, "expires_at": None}


def update_subscription(user_id: str, data: dict[str, Any]) -> dict | None:
    """
    Partial update on the most recent subscription row for user_id.
    Accepts keys: plan, status, expires_at.
    """
    _VALID = {"plan", "status", "expires_at"}
    payload = {k: v for k, v in data.items() if k in _VALID}

    if not payload:
        log.warning("update_subscription: no valid fields in %s", data)
        return get_subscription(user_id)

    try:
        # Target only the latest subscription row via a subquery workaround:
        # Supabase PostgREST doesn't support ORDER+LIMIT on UPDATE, so we
        # first fetch the id, then update by id.
        existing = get_subscription(user_id)
        if not existing or not existing.get("id"):
            return None

        res = (
            _client()
            .table("subscriptions")
            .update(payload)
            .eq("id", existing["id"])
            .execute()
        )
        if res.data:
            return _row_to_dict(res.data[0])
    except Exception as exc:
        log.error("update_subscription(%s) failed: %s", user_id, exc)

    return get_subscription(user_id)


def cancel_subscription(user_id: str) -> bool:
    """
    Sets status to 'cancelled' on the active subscription.
    Returns True on success, False otherwise.
    """
    result = update_subscription(user_id, {"status": "cancelled"})
    return result is not None and result.get("status") == "cancelled"


def is_active(user_id: str) -> bool:
    """
    Returns True if the user has an active, non-expired subscription.
    Free plan is always considered active.
    """
    sub = get_subscription(user_id)
    if sub is None:
        return False  # No subscription at all
    if sub.get("status") != "active":
        return False
    if _is_expired(sub):
        # Lazily mark it expired
        update_subscription(user_id, {"status": "expired"})
        return False
    return True
