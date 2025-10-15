# app/services/db.py

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import settings

_engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, future=True)

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        if not settings.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")
        _engine = create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=settings.PG_POOL_SIZE,
            max_overflow=settings.PG_MAX_OVERFLOW,
            pool_pre_ping=settings.PG_POOL_PRE_PING,
            future=True,
        )
        SessionLocal.configure(bind=_engine)
    return _engine

def get_db():
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()