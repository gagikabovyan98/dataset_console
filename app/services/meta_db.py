# app/services/meta_db.py

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import settings

_meta_engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, future=True)

def get_meta_engine() -> Engine:
    global _meta_engine
    if _meta_engine is None:
        if not settings.META_DATABASE_URL:
            raise RuntimeError("META_DATABASE_URL is not set")
        _meta_engine = create_engine(
            settings.META_DATABASE_URL,
            poolclass=QueuePool,
            pool_size=settings.PG_POOL_SIZE,
            max_overflow=settings.PG_MAX_OVERFLOW,
            pool_pre_ping=settings.PG_POOL_PRE_PING,
            future=True,
        )
        SessionLocal.configure(bind=_meta_engine)
    return _meta_engine


def get_meta_db():
    get_meta_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
