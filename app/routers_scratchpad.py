# app/routers_scratchpad.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from app.services.meta_db import SessionLocal
from app.models.meta_models import DCWorkspace, DCScratchpad

UTC = timezone.utc
scratchpad_router = APIRouter()

# ---------- Pydantic ----------

class PutScratchpad(BaseModel):
    key: str
    kind: str = Field(..., description="json | scalar | parquet | bytes | ch_table")
    value_json: Optional[Any] = None
    value: Optional[Any] = Field(None, description="alias for value_json")
    uri: Optional[str] = None
    ttl_minutes: int = Field(120, ge=1, le=7*24*60)
    workspace: str = "default"

    @model_validator(mode="after")
    def _normalize(cls, m: "PutScratchpad"):
        if m.value_json is None and m.value is not None:
            m.value_json = m.value
        if m.value_json is None and m.uri is None:
            raise ValueError("either value_json or uri must be provided")
        return m

class ScratchpadResponse(BaseModel):
    id: int
    workspace: str
    key: str
    kind: str
    value_json: Optional[Any] = None
    uri: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

def _to_resp(obj: DCScratchpad, ws_name: str) -> ScratchpadResponse:
    return ScratchpadResponse(
        id=obj.id,
        workspace=ws_name,
        key=obj.key,
        kind=obj.kind,
        value_json=obj.value_json,
        uri=obj.uri,
        created_at=obj.created_at,
        expires_at=obj.expires_at,
    )

# ---------- Helpers ----------

def _ensure_workspace(s, name: str) -> DCWorkspace:
    ws = s.scalar(select(DCWorkspace).where(DCWorkspace.name == name))
    if not ws:
        ws = DCWorkspace(name=name)
        s.add(ws)
        s.commit()
        s.refresh(ws)
    return ws

# ---------- Routes ----------

@scratchpad_router.put("/scratchpad", response_model=ScratchpadResponse)
def put_scratchpad(payload: PutScratchpad = Body(...)):
    with SessionLocal() as s:
        ws = _ensure_workspace(s, payload.workspace)

        obj = s.scalar(
            select(DCScratchpad).where(
                DCScratchpad.workspace_id == ws.id,
                DCScratchpad.key == payload.key,
            )
        )
        now = datetime.now(UTC)
        exp = now + timedelta(minutes=payload.ttl_minutes)

        if obj:
            obj.kind = payload.kind
            obj.value_json = payload.value_json
            obj.uri = payload.uri
            obj.expires_at = exp
        else:
            obj = DCScratchpad(
                workspace_id=ws.id,
                key=payload.key,
                kind=payload.kind,
                value_json=payload.value_json,
                uri=payload.uri,
                expires_at=exp,
            )
            s.add(obj)

        try:
            s.commit()
        except IntegrityError as e:
            s.rollback()
            raise HTTPException(status_code=409, detail=f"Conflict: {str(e)}")

        s.refresh(obj)
        return _to_resp(obj, ws.name)

@scratchpad_router.get("/scratchpad/{key}", response_model=ScratchpadResponse)
def get_scratchpad(
    key: str,
    workspace: str = Query("default"),
    allow_expired: bool = Query(False, description="если true — не удаляем протухшие записи"),
):
    with SessionLocal() as s:
        ws = s.scalar(select(DCWorkspace).where(DCWorkspace.name == workspace))
        if not ws:
            raise HTTPException(status_code=404, detail=f"workspace '{workspace}' not found")

        obj = s.scalar(
            select(DCScratchpad).where(
                DCScratchpad.workspace_id == ws.id,
                DCScratchpad.key == key,
            )
        )
        if not obj:
            raise HTTPException(status_code=404, detail="key not found")

        if obj.expires_at and obj.expires_at < datetime.now(UTC) and not allow_expired:
            s.execute(
                delete(DCScratchpad).where(
                    DCScratchpad.id == obj.id
                )
            )
            s.commit()
            raise HTTPException(status_code=404, detail="key expired")

        return _to_resp(obj, ws.name)

@scratchpad_router.delete("/scratchpad/{key}")
def delete_scratchpad(
    key: str,
    workspace: str = Query("default"),
):
    with SessionLocal() as s:
        ws = s.scalar(select(DCWorkspace).where(DCWorkspace.name == workspace))
        if not ws:
            return {"ok": True, "deleted": 0}
        obj = s.scalar(
            select(DCScratchpad).where(
                DCScratchpad.workspace_id == ws.id,
                DCScratchpad.key == key,
            )
        )
        if not obj:
            return {"ok": True, "deleted": 0}
        s.execute(delete(DCScratchpad).where(DCScratchpad.id == obj.id))
        s.commit()
        return {"ok": True, "deleted": 1}
