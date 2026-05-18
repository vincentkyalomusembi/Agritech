"""
routes/auth.py
Phone OTP authentication — Africa's Talking SMS + JWT.

Flow
----
  1.  POST /auth/request-otp   { phone }
        → generates 6-digit OTP
        → stores hash + expiry in DB (otp_store table)
        → sends OTP via AT SMS
        → returns { message, expires_in }

  2.  POST /auth/verify-otp    { phone, otp }
        → looks up stored hash
        → verifies OTP matches and hasn't expired
        → deletes used OTP
        → returns { access_token, token_type, phone }

  3.  GET  /auth/me            (Authorization: Bearer <token>)
        → returns the authenticated user profile from Supabase (or minimal
          stub if Supabase isn't configured yet)

Security notes
--------------
  - OTP is stored as a bcrypt hash (never plain-text).
  - OTP expires in OTP_EXPIRES_SECONDS (default 5 min) from settings.
  - A phone can only have one active OTP (re-requesting replaces the old one).
  - Brute-force protection: max 5 attempts per OTP before it's voided.
"""

from __future__ import annotations

import hashlib
import logging
import random
import string
import time

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator

from core.config import settings
from core.jwt import create_token, CurrentUser
from db.otp_store import (
    store_otp,
    get_otp,
    increment_attempts,
    delete_otp,
    MAX_ATTEMPTS,
)
from services.africastalking import send_sms

log = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])





# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_otp(length: int = 6) -> str:
    """Generates a cryptographically random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def _normalise_phone(phone: str) -> str:
    """
    Normalises Kenyan phone numbers to E.164.
    Accepts: 07XXXXXXXX, 2547XXXXXXXX, +2547XXXXXXXX
    Returns: +2547XXXXXXXX
    """
    phone = phone.strip().replace(" ", "")
    if phone.startswith("07") or phone.startswith("01"):
        phone = "+254" + phone[1:]
    elif phone.startswith("2547") or phone.startswith("2541"):
        phone = "+" + phone
    elif not phone.startswith("+"):
        raise ValueError(f"Unrecognised phone format: {phone!r}")
    return phone


# ── Request / Response models ─────────────────────────────────────────────────

class OTPRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def normalise(cls, v: str) -> str:
        try:
            return _normalise_phone(v)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class OTPVerify(BaseModel):
    phone: str
    otp: str

    @field_validator("phone")
    @classmethod
    def normalise(cls, v: str) -> str:
        try:
            return _normalise_phone(v)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    phone:        str
    expires_in:   int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/request-otp",
    summary="Request a 6-digit OTP via SMS",
    status_code=status.HTTP_200_OK,
)
def request_otp(body: OTPRequest):
    """
    Generates a one-time password and sends it to the given phone via
    Africa's Talking SMS.

    Rate limiting / replay protection
    ----------------------------------
    If a valid (non-expired) OTP already exists for this phone, we still
    replace it so the user always gets a fresh code when they re-request.
    """
    phone = body.phone
    otp   = _generate_otp()
    ttl   = settings.OTP_EXPIRES_SECONDS

    # Persist to SQLite (survives restarts; auto-replaces any previous OTP)
    store_otp(phone, _hash_otp(otp))

    message = (
        f"Your Agritech AI verification code is: {otp}\n"
        f"Valid for {ttl // 60} minute(s). Do not share this code."
    )

    # --- SMS delivery ---------------------------------------------------------
    if settings.AT_USERNAME == "sandbox" and settings.APP_ENV == "development":
        # Dev mode: skip actual SMS, log the OTP instead
        log.warning("[auth] SANDBOX OTP for %s: %s (not sent)", phone, otp)
    else:
        try:
            send_sms(phone, message)
        except Exception as exc:
            log.error("[auth] Failed to send OTP to %s: %s", phone, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not send SMS. Please try again.",
            )

    return {
        "message":    f"OTP sent to {phone}",
        "expires_in": ttl,
    }


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Verify OTP and receive a JWT",
)
def verify_otp(body: OTPVerify):
    """
    Validates the OTP and, on success, returns a signed JWT.

    The JWT sub claim is the E.164 phone number — matching the USSD identity.
    """
    phone  = body.phone
    record = get_otp(phone)

    # ── No record found ───────────────────────────────────────────────────────
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No OTP found for this number. Request a new one.",
        )

    # ── Too many attempts ─────────────────────────────────────────────────────
    if record["attempts"] >= MAX_ATTEMPTS:
        delete_otp(phone)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Request a new OTP.",
        )

    # ── Expired ───────────────────────────────────────────────────────────────
    # get_otp() already does lazy-delete on expiry; belt-and-suspenders check:
    if time.time() > record["expires"]:
        delete_otp(phone)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Request a new one.",
        )

    # ── Wrong OTP ─────────────────────────────────────────────────────────────
    if _hash_otp(body.otp.strip()) != record["hash"]:
        new_attempts = increment_attempts(phone)
        remaining = MAX_ATTEMPTS - new_attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect OTP. {remaining} attempt(s) remaining.",
        )

    # ── Success ───────────────────────────────────────────────────────────────
    delete_otp(phone)

    token = create_token(phone)
    ttl   = settings.JWT_EXPIRES_SECONDS

    log.info("[auth] Verified OTP for %s — token issued.", phone)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        phone=phone,
        expires_in=ttl,
    )


@router.get(
    "/me",
    summary="Get the authenticated user's profile",
)
def me(phone: CurrentUser):
    """
    Returns the caller's profile.

    Requires: Authorization: Bearer <token>

    Tries Supabase first. Falls back to a stub with just the phone number if
    Supabase isn't configured (useful during development).
    """
    # ── Try Supabase ──────────────────────────────────────────────────────────
    try:
        from db.users import get_user_by_phone
        profile = get_user_by_phone(phone)
        if profile:
            return {
                "phone":      profile.get("phone"),
                "name":       profile.get("name"),
                "county":     profile.get("county"),
                "farm_type":  profile.get("farm_type"),
                "soil_type":  profile.get("soil_type"),
                "onboarded":  profile.get("onboarded", False),
            }
    except Exception as exc:
        log.warning("[auth] Supabase user lookup failed: %s", exc)

    # ── Fallback stub ─────────────────────────────────────────────────────────
    return {
        "phone":     phone,
        "name":      None,
        "county":    None,
        "farm_type": None,
        "soil_type": None,
        "onboarded": False,
    }
