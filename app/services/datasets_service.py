# app/services/datasets_service.py

from typing import List, Dict, Tuple
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.services.db import get_engine

def get_pg_engine() -> Engine:
    return get_engine()

def fetch_dataset_map(ids: List[int]) -> Dict[int, Tuple[str, str]]:
    if not ids:
        return {}
    eng = get_pg_engine()
    sql = text("""
        SELECT id,
               COALESCE(title, 'Dataset ' || id::text) AS title,
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
