# app/routers/scripts.py

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

from app.services.db import get_db
from app.models.meta_models import DCScript, DCWorkspace

router = APIRouter(prefix="/workspaces/{ws_id}/scripts", tags=["scripts"])

class ScriptIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str
    meta: Optional[dict] = None

class ScriptOut(BaseModel):
    id: int
    name: str
    workspace_id: int
    created_at: datetime
    updated_at: datetime | None = None
    class Config:
        from_attributes = True

class ScriptOutWithCode(BaseModel):
    id: int
    name: str
    workspace_id: int
    code: str
    created_at: datetime
    updated_at: datetime | None = None
    class Config:
        from_attributes = True

class ScriptPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = None
    meta: Optional[dict] = None


@router.get("", response_model=List[ScriptOut])
def list_scripts(
    ws_id: int = Path(...),
    q: Optional[str] = Query(None, description="search in name"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    ws = db.get(DCWorkspace, ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace not found")
    stmt = select(DCScript).where(DCScript.workspace_id == ws_id).order_by(DCScript.id.desc()).limit(limit)
    if q:
        from sqlalchemy import func
        stmt = stmt.where(func.lower(DCScript.name).like(f"%{q.lower()}%"))
    return list(db.execute(stmt).scalars())

@router.post("", response_model=ScriptOut)
def create_script(
    payload: ScriptIn,
    ws_id: int = Path(...),
    db: Session = Depends(get_db),
):
    ws = db.get(DCWorkspace, ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace not found")

    exists = db.execute(
        select(DCScript).where(DCScript.workspace_id == ws_id, DCScript.name == payload.name)
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="script name already exists in workspace")

    obj = DCScript(
        workspace_id=ws_id,
        name=payload.name.strip(),
        code=payload.code,
        meta=payload.meta or {},
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.patch("/{script_id}", response_model=ScriptOut)
def update_script(
    script_id: int,
    payload: ScriptPatch,
    ws_id: int = Path(...),
    db: Session = Depends(get_db),
):
    obj = db.get(DCScript, script_id)
    if not obj or obj.workspace_id != ws_id:
        raise HTTPException(status_code=404, detail="script not found")
    if payload.name is not None:
        exists = db.execute(
            select(DCScript).where(DCScript.workspace_id == ws_id, DCScript.name == payload.name, DCScript.id != script_id)
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=409, detail="script name already exists in workspace")
        obj.name = payload.name.strip()
    if payload.code is not None:
        obj.code = payload.code
    if payload.meta is not None:
        obj.meta = payload.meta
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.delete("/{script_id}")
def delete_script(
    script_id: int,
    ws_id: int = Path(...),
    db: Session = Depends(get_db),
):
    obj = db.get(DCScript, script_id)
    if not obj or obj.workspace_id != ws_id:
        return {"ok": True, "deleted": 0}
    db.delete(obj); db.commit()
    return {"ok": True, "deleted": 1}

@router.get("/{script_id}", response_model=ScriptOutWithCode)
def get_script_by_id(
    script_id: int,
    ws_id: int = Path(...),
    db: Session = Depends(get_db),
):
    obj = db.get(DCScript, script_id)
    if not obj or obj.workspace_id != ws_id:
        raise HTTPException(status_code=404, detail="script not found")
    return obj

@router.get("/by_name/{name}", response_model=ScriptOutWithCode)
def get_script_by_name(
    name: str,
    ws_id: int = Path(...),
    db: Session = Depends(get_db),
):
    obj = db.execute(
        select(DCScript).where(
            DCScript.workspace_id == ws_id,
            DCScript.name == name
        )
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="script not found")
    return obj