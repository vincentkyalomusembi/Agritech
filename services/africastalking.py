"""
services/africastalking.py
Africa's Talking gateway — SMS sending only.

Responsibilities
----------------
  send_sms(phone, message)  — sends a plain SMS via the AT REST API.
                              Used by routes/auth.py to deliver OTPs.

Why not use the AT Python SDK?
-------------------------------
  The official SDK (africastalking-python) is a heavy dependency and pulls in
  eventlet. We only need one endpoint, so we call the REST API directly with
  requests. This keeps the dependency footprint minimal.

Sandbox vs production
---------------------
  AT_USERNAME = "sandbox"  → hits https://api.sandbox.africastalking.com
  AT_USERNAME = <real>     → hits https://api.africastalking.com

  The sandbox accepts any phone number and doesn't actually send SMS.
  Set AT_USERNAME to your real username in production.
"""

from __future__ import annotations

import logging

import requests

from core.config import settings

log = logging.getLogger(__name__)


# ── Endpoints ─────────────────────────────────────────────────────────────────

_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"
_PROD_URL    = "https://api.africastalking.com/version1/messaging"
_TIMEOUT     = 10  # seconds


def _sms_url() -> str:
    return _SANDBOX_URL if settings.AT_USERNAME == "sandbox" else _PROD_URL


# ── Public API ────────────────────────────────────────────────────────────────

def send_sms(phone: str, message: str) -> dict:
    """
    Sends an SMS to the given phone number via Africa's Talking.

    Args:
        phone:   E.164 number, e.g. "+254712345678".
        message: SMS body (160 chars max for single SMS).

    Returns:
        AT API response dict.

    Raises:
        RuntimeError if AT credentials are not configured.
        requests.HTTPError on non-2xx response.
    """
    if not settings.AT_API_KEY:
        raise RuntimeError(
            "AT_API_KEY is not set. Add it to .env to send SMS."
        )

    headers = {
        "apiKey":       settings.AT_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept":       "application/json",
    }

    payload = {
        "username": settings.AT_USERNAME,
        "to":       phone,
        "message":  message,
    }

    try:
        response = requests.post(
            _sms_url(),
            data=payload,
            headers=headers,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        log.info("[AT] SMS sent to %s: %s", phone, result)
        return result

    except requests.HTTPError as exc:
        log.error("[AT] SMS failed for %s: %s — %s", phone, exc, exc.response.text)
        raise
    except requests.RequestException as exc:
        log.error("[AT] SMS network error for %s: %s", phone, exc)
        raise
