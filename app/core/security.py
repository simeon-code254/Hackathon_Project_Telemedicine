"""
Compatibility shim.

This module previously imported from `app.db.session`, `app.models.patient` and
`app.models.doctor` — none of which exist in this repository, so every import of
`app.core.security` raised ImportError. The real, working, async auth module is
`backend/app/core/security.py`, wired to the SQLAlchemy models and the FastAPI
app in backend/main.py (JWT access + refresh tokens, bcrypt hashing, a
timing-safe login check).

This file re-exports that module's public API, so any legacy import of
`app.core.security` keeps working. New code should import from
backend.app.core.security directly.
"""

from backend.app.core.security import (  # noqa: F401
    pwd_context,
    oauth2_scheme,
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    authenticate_patient,
    get_current_patient,
    get_current_doctor,
    get_current_patient_alternative,
)
from backend.app.core.config import settings  # noqa: F401

__all__ = [
    "pwd_context",
    "oauth2_scheme",
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "decode_token",
    "authenticate_patient",
    "get_current_patient",
    "get_current_doctor",
    "get_current_patient_alternative",
    "settings",
]
