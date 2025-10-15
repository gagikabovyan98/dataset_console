# app/services/db_init.py

from __future__ import annotations
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.db import get_engine, SessionLocal
from app.models.meta_models import Base, DCWorkspace

def init_db():
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS dataset_console"))
    Base.metadata.create_all(bind=eng)

    with SessionLocal() as s:
        ws = s.query(DCWorkspace).filter(DCWorkspace.name == "default").one_or_none()
        if not ws:
            s.add(DCWorkspace(name="default", usergroup_id=None))
            s.commit()