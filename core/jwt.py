"""
core/jwt.py
JWT utilities — issue and verify access tokens.

Token payload
-------------
  sub   : phone number (E.164, e.g. "+254712345678") — matches USSD identity
  iat   : issued-at (Unix seconds)
  exp   : expiry (Unix seconds)
  type  : "access"

Usage
-----
  token = create_token("+254712345678")
  phone = verify_token(token)           # raises HTTPException on invalid/expired
  phone = get_current_user(request)     # FastAPI dependency — reads Authorization header
"""

from __future__ import annotations

import time
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status

from core.config import settings


# ── Constants ─────────────────────────────────────────────────────────────────

_ALGORITHM = "HS256"
_TOKEN_TYPE = "access"


# ── Token creation ────────────────────────────────────────────────────────────

def create_token(phone: str, expires_in: int | None = None) -> str:
    """
    Creates a signed JWT for the given phone number.

    Args:
        phone:      E.164 phone number — the canonical user identity.
        expires_in: Lifetime in seconds. Defaults to settings.JWT_EXPIRES_SECONDS.

    Returns:
        Signed JWT string.
    """
    if not settings.JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET is not set. Add it to .env before issuing tokens."
        )

    ttl = expires_in if expires_in is not None else settings.JWT_EXPIRES_SECONDS
    now = int(time.time())

    payload = {
        "sub":  phone,
        "iat":  now,
        "exp":  now + ttl,
        "type": _TOKEN_TYPE,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


# ── Token verification ────────────────────────────────────────────────────────

def verify_token(token: str) -> str:
    """
    Decodes and validates a JWT.

    Returns:
        The phone number (sub claim).

    Raises:
        HTTPException 401 on expired, invalid signature, or wrong type.
    """
    if not settings.JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth not configured (missing JWT_SECRET).",
        )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Request a new OTP.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != _TOKEN_TYPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    phone: str | None = payload.get("sub")
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has no subject.",
        )

    return phone


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """
    FastAPI dependency — extracts and verifies the Bearer token from the
    Authorization header.

    Usage:
        @router.get("/protected")
        def protected(phone: str = Depends(get_current_user)):
            return {"phone": phone}

    Returns:
        Verified phone number string.

    Raises:
        HTTPException 401 if the header is missing or the token is invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authorization header must be "Bearer <token>".',
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(token)


# Alias — lets routes import a more expressive name
CurrentUser = Annotated[str, Depends(get_current_user)]
