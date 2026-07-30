"""
Compatibility shim.

This module previously imported from `app.db.session`, `app.models.patient` and
`app.models.doctor` — none of which exist in this repository, so every import of
`app.core.security` raised ImportError. The working, tested auth utilities live in
`backend/app/core/security.py` (synchronous, wired to the real SQLAlchemy models
and the running FastAPI app in backend/main.py).

This file now re-exports those, so any legacy import path keeps working without
the broken references. New code should import from backend.app.core.security.
"""

from backend.app.core.security import (  # noqa: F401
    pwd_context,
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
    get_current_patient,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

__all__ = [
    "pwd_context",
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "decode_token",
    "get_current_patient",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
]
