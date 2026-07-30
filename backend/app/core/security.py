"""
Authentication utilities: password hashing (passlib/bcrypt) and JWT (python-jose),
plus a FastAPI dependency that resolves the current patient from a Bearer token.

Synchronous to match the running backend (backend/main.py) and its sync DB layer.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models.database import Patient

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))

# pbkdf2_sha256: pure-Python, no native bcrypt version fragility, no 72-byte cap.
# (passlib+bcrypt 4.x have a known incompatibility.) Still a strong, salted KDF.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# auto_error=False so we can raise a consistent, accessibility-friendly 401.
bearer_scheme = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: Optional[str]) -> bool:
    if not hashed:
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(subject: str, extra: Optional[dict] = None) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_patient(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Patient:
    """Resolve the authenticated patient, or raise 401."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not creds or not creds.credentials:
        raise credentials_exception
    payload = decode_token(creds.credentials)
    if not payload:
        raise credentials_exception
    patient_uuid = payload.get("sub")
    if not patient_uuid:
        raise credentials_exception
    patient = db.query(Patient).filter(Patient.uuid == patient_uuid).first()
    if patient is None:
        raise credentials_exception
    if not patient.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return patient
