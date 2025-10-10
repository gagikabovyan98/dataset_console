# app/services/datasets_service.py

from typing import List, Dict, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from app.config import settings

_pg_engine: Engine | None = None

def get_pg_engine() -> Engine:
    global _pg_engine
    if _pg_engine is None:
        if not settings.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")
        _pg_engine = create_engine(
            settings.DATABASE_URL,
            pool_size=getattr(settings, "PG_POOL_SIZE", 5),
            max_overflow=getattr(settings, "PG_MAX_OVERFLOW", 5),
            pool_pre_ping=getattr(settings, "PG_POOL_PRE_PING", True),
            future=True,
        )
    return _pg_engine

def fetch_dataset_map(ids: List[int]) -> Dict[int, Tuple[str, str]]:
    if not ids:
        return {}
    eng = get_pg_engine()
    sql = text("""
        SELECT id,
               COALESCE(title, CONCAT('Dataset ', id::text)) AS title,
               ch_table_name
        FROM datasets
        WHERE id = ANY(:ids)
    """)
    out: Dict[int, Tuple[str, str]] = {}
    with eng.connect() as conn:
        rows = conn.execute(sql, {"ids": ids}).mappings().all()
        for r in rows:
            out[int(r["id"])] = (str(r["title"]), str(r["ch_table_name"]))
    return out
