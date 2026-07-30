"""
Database session/engine layer (synchronous SQLAlchemy 2.0).

Defaults to a local SQLite file so the backend runs out of the box with no
Postgres/Redis needed. Set DATABASE_URL to point at Postgres in production, e.g.
    postgresql+psycopg://user:pass@host/afyaconnect
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.app.models.database import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./afyaconnect.db")

# SQLite + a threaded FastAPI server needs check_same_thread disabled.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create all tables. Safe to call repeatedly (create_all is idempotent)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency yielding a request-scoped DB session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
