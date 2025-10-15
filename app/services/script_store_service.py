# app/services/script_store_service.py

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.services.db import SessionLocal
from app.models.meta_models import DCScript, DCWorkspace

def _resolve_ws_by_name(s: Session, workspace_name: str) -> DCWorkspace:
    ws = s.scalar(select(DCWorkspace).where(DCWorkspace.name == workspace_name))
    if not ws:
        ws = DCWorkspace(name=workspace_name)
        s.add(ws); s.commit(); s.refresh(ws)
    return ws

def create_script(name: str, code: str, meta: dict | None = None, *, workspace_id: int | None = None, workspace_name: str | None = "default") -> int:
    with SessionLocal() as s:
        if workspace_id is None:
            ws = _resolve_ws_by_name(s, workspace_name or "default")
            workspace_id = ws.id
        exists = s.scalar(select(DCScript).where(DCScript.workspace_id == workspace_id, DCScript.name == name))
        if exists:
            raise ValueError("script name already exists in workspace")
        script = DCScript(name=name, code=code, meta=meta or {}, workspace_id=workspace_id)
        s.add(script); s.commit(); s.refresh(script)
        return script.id

def update_script(script_id: int, name: str | None = None, code: str | None = None, meta: dict | None = None) -> None:
    with SessionLocal() as s:
        obj = s.get(DCScript, script_id)
        if not obj:
            return
        if name is not None:
            exists = s.scalar(select(DCScript).where(DCScript.workspace_id == obj.workspace_id, DCScript.name == name, DCScript.id != obj.id))
            if exists:
                raise ValueError("script name already exists in workspace")
            obj.name = name
        if code is not None: obj.code = code
        if meta is not None: obj.meta = meta
        s.commit()

def get_script(script_id: int) -> Optional[dict]:
    with SessionLocal() as s:
        obj = s.get(DCScript, script_id)
        if not obj:
            return None
        return {
            "id": obj.id,
            "name": obj.name,
            "code": obj.code,
            "meta": obj.meta,
            "workspace_id": obj.workspace_id,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }

def list_scripts(*, workspace_id: int, limit: int = 100) -> list[dict]:
    with SessionLocal() as s:
        rows = s.scalars(
            select(DCScript)
            .where(DCScript.workspace_id == workspace_id)
            .order_by(DCScript.id.desc())
            .limit(limit)
        ).all()
        return [
            {"id": r.id, "name": r.name, "created_at": r.created_at, "updated_at": r.updated_at, "workspace_id": r.workspace_id}
            for r in rows
        ]