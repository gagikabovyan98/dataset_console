# app/routers/workspaces.py

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session
from app.models.meta_models import DCModule, DCScript, DCArtifact

from app.services.db import get_db
from app.models.meta_models import DCWorkspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

class WorkspaceIn(BaseModel):
    name: str
    usergroup_id: int | None = None

class WorkspaceOut(BaseModel):
    id: int
    name: str
    usergroup_id: int | None

    class Config:
        from_attributes = True

class WorkspaceStats(BaseModel):
    id: int
    name: str
    usergroup_id: int | None
    modules: int
    scripts: int
    artifacts: int

def _ensure_unique_name(db: Session, name: str):
    exists = db.scalar(select(DCWorkspace).where(DCWorkspace.name == name))
    if exists:
        raise HTTPException(status_code=409, detail="workspace name already exists")


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(db: Session = Depends(get_db)):
    rows = db.scalars(select(DCWorkspace)).all()
    return rows

@router.post("", response_model=WorkspaceOut)
def create_workspace(
    payload: WorkspaceIn,
    db: Session = Depends(get_db)
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    _ensure_unique_name(db, name)
    ws = DCWorkspace(name=name, usergroup_id=payload.usergroup_id)
    db.add(ws); db.commit(); db.refresh(ws)
    return ws

@router.delete("/{ws_id}", response_model=dict)
def delete_workspace(
    ws_id: int,
    db: Session = Depends(get_db)
):
    ws = db.get(DCWorkspace, ws_id)
    if not ws:
        return {"ok": True, "deleted": 0}

    db.execute(delete(DCWorkspace).where(DCWorkspace.id == ws_id))
    db.commit()
    return {"ok": True, "deleted": 1}

@router.get("/{ws_id}/stats", response_model=WorkspaceStats)
def workspace_stats(
    ws_id: int,
    db: Session = Depends(get_db)
):
    ws = db.get(DCWorkspace, ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Not found")

    modules_cnt = db.scalar(select(func.count()).select_from(DCModule).where(DCModule.workspace_id == ws_id)) or 0
    scripts_cnt = db.scalar(select(func.count()).select_from(DCScript).where(DCScript.workspace_id == ws_id)) or 0
    artifacts_cnt = db.scalar(select(func.count()).select_from(DCArtifact).where(DCArtifact.workspace_id == ws_id)) or 0

    return WorkspaceStats(
        id=ws.id,
        name=ws.name,
        usergroup_id=ws.usergroup_id,
        modules=modules_cnt,
        scripts=scripts_cnt,
        artifacts=artifacts_cnt,
    )