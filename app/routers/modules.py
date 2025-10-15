# app/routers/modules.py

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.meta_models import DCWorkspace, DCModule
from app.services.db import get_db
from app.services import module_service
from datetime import datetime


ws_router = APIRouter(prefix="/workspaces/{ws_id}/modules", tags=["modules"])

class ModuleIn(BaseModel):
    name: str = Field(..., description="Python module name, e.g. 'console1'")
    code: str = Field(..., description="Python source code (.py)")
    is_private: Optional[bool] = False

class ModuleOut(BaseModel):
    id: int
    name: str
    is_published: bool
    published_at: datetime | None = None
    class Config:
        from_attributes = True

@ws_router.get("", response_model=List[ModuleOut])
def ws_list_modules(
    ws_id: int = Path(...),
    published_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    ws = db.get(DCWorkspace, ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace not found")
    mods = module_service.list_modules(
        db, workspace_id=ws_id, user_id=None, usergroup_id=None, published_only=published_only
    )
    return mods

@ws_router.post("", response_model=ModuleOut)
def ws_save_module_draft(
    ws_id: int = Path(...),
    payload: ModuleIn = ...,
    db: Session = Depends(get_db),
):
    ws = db.get(DCWorkspace, ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace not found")
    try:
        mod = module_service.save_or_update_draft(
            db,
            name=payload.name,
            code=payload.code,
            workspace_id=ws_id,
            usergroup_id=None,
            added_by_user_id=None,
            is_private=bool(payload.is_private),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return mod

@ws_router.post("/{module_id}/publish", response_model=ModuleOut)
def ws_publish_module(
    ws_id: int = Path(...),
    module_id: int = Path(...),
    db: Session = Depends(get_db),
):
    mod = db.get(DCModule, module_id)
    if not mod or mod.workspace_id != ws_id:
        raise HTTPException(status_code=404, detail="Module not found in this workspace")
    try:
        mod = module_service.publish_module(db, module_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return mod

@ws_router.delete("/{module_id}")
def ws_delete_module(
    ws_id: int = Path(...),
    module_id: int = Path(...),
    db: Session = Depends(get_db),
):
    mod = db.get(DCModule, module_id)
    if not mod or mod.workspace_id != ws_id:
        return {"ok": True, "deleted": 0}
    deleted = module_service.delete_module(db, module_id)
    return {"ok": True, "deleted": int(bool(deleted))}
