# app/routers/scratchpad.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db import get_db
from app.models.meta_models import DCWorkspace, DCScratchpad

router = APIRouter(tags=["scratchpad"])

class ScratchpadPut(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    kind: Literal["json", "parquet", "bytes", "ch_table", "scalar"]
    value_json: Any | None = None
    uri: str | None = None
    ttl_minutes: int = Field(60, ge=1, le=7 * 24 * 60)
    workspace: str = Field(..., min_length=1, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def normalize_before(cls, data: dict):
        if not isinstance(data, dict):
            return data
        kind = data.get("kind")
        if kind in ("json", "scalar"):
            data.setdefault("value_json", None)
            data["uri"] = None
        else:
            data["value_json"] = None
        return data

    @model_validator(mode="after")
    def validate_after(self):
        if self.kind in ("json", "scalar"):
            if self.value_json is None:
                raise ValueError("value_json is required for kind=json|scalar")
        else:
            if not self.uri:
                raise ValueError("uri is required for kind=parquet|bytes|ch_table")
        return self


class ScratchpadAckOut(BaseModel):
    ok: bool
    created: bool | None = None
    updated: bool | None = None
    key: str
    workspace_id: int


class ScratchpadItemOut(BaseModel):
    key: str
    kind: Literal["json", "parquet", "bytes", "ch_table", "scalar"]
    value_json: Any | None = None
    uri: str | None = None
    expires_at: datetime
    workspace_id: int

    class Config:
        from_attributes = True


def _get_or_create_ws(db: Session, ws_name: str) -> DCWorkspace:
    ws = db.scalar(select(DCWorkspace).where(DCWorkspace.name == ws_name))
    if ws:
        return ws
    ws = DCWorkspace(name=ws_name, usergroup_id=None)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def _get_ws_required(db: Session, ws_name: str) -> DCWorkspace:
    ws = db.scalar(select(DCWorkspace).where(DCWorkspace.name == ws_name))
    if not ws:
        raise HTTPException(status_code=404, detail="workspace not found")
    return ws


@router.put("/scratchpad", response_model=ScratchpadAckOut)
def put_scratchpad(payload: ScratchpadPut, db: Session = Depends(get_db)):
    ws = _get_or_create_ws(db, payload.workspace)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=payload.ttl_minutes)

    row = db.scalar(
        select(DCScratchpad).where(
            DCScratchpad.workspace_id == ws.id,
            DCScratchpad.key == payload.key,
        )
    )

    if row:
        row.kind = payload.kind
        row.value_json = payload.value_json
        row.uri = payload.uri
        row.expires_at = expires_at
        db.add(row)
        db.commit()
        db.refresh(row)
        return ScratchpadAckOut(ok=True, updated=True, key=row.key, workspace_id=ws.id)

    obj = DCScratchpad(
        workspace_id=ws.id,
        key=payload.key,
        kind=payload.kind,
        value_json=payload.value_json,
        uri=payload.uri,
        expires_at=expires_at,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ScratchpadAckOut(ok=True, created=True, key=obj.key, workspace_id=ws.id)


@router.get("/scratchpad/{key}", response_model=ScratchpadItemOut)
def get_scratchpad(
    key: str = Path(..., min_length=1),
    workspace: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    ws = _get_ws_required(db, workspace)
    row = db.scalar(
        select(DCScratchpad).where(
            DCScratchpad.workspace_id == ws.id,
            DCScratchpad.key == key,
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="scratchpad key not found")
    return ScratchpadItemOut.model_validate(row)


@router.get("/scratchpad", response_model=List[ScratchpadItemOut])
def list_scratchpad(
    workspace: str = Query(..., description="Workspace name"),
    prefix: Optional[str] = Query(None, description="Filter by key prefix"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    ws = _get_ws_required(db, workspace)
    stmt = (
        select(DCScratchpad)
        .where(DCScratchpad.workspace_id == ws.id)
        .order_by(DCScratchpad.key.asc())
        .limit(limit)
    )
    if prefix:
        stmt = stmt.where(DCScratchpad.key.like(f"{prefix}%"))

    rows = list(db.execute(stmt).scalars())
    return [ScratchpadItemOut.model_validate(r) for r in rows]


@router.delete("/scratchpad/{key}", response_model=dict)
def delete_scratchpad(
    key: str = Path(..., min_length=1),
    workspace: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    ws = _get_ws_required(db, workspace)
    row = db.scalar(
        select(DCScratchpad).where(
            DCScratchpad.workspace_id == ws.id,
            DCScratchpad.key == key,
        )
    )
    if not row:
        return {"ok": True, "deleted": 0}
    db.delete(row)
    db.commit()
    return {"ok": True, "deleted": 1}