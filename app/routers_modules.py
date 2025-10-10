# app/routers_modules.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from app.services.meta_db import get_meta_db
from app.services import module_service
from app.utils.auth import parse_user_ctx
from app.services.workspace_service import resolve_workspace_id

routers_modules = APIRouter(prefix="/modules", tags=["modules"])

class ModuleIn(BaseModel):
    name: str = Field(..., description="Python module name, e.g. 'console1'")
    code: str = Field(..., description="Python source code (.py)")
    is_private: Optional[bool] = False

class ModuleOut(BaseModel):
    id: int
    name: str
    is_published: bool
    published_at: Optional[str] = None
    class Config:
        from_attributes = True

@routers_modules.post("", response_model=ModuleOut)
def save_module_draft(payload: ModuleIn, request: Request, db: Session = Depends(get_meta_db)):
    user_id, usergroup_id = parse_user_ctx(request)
    ws_id = resolve_workspace_id(db, usergroup_id)
    try:
        mod = module_service.save_or_update_draft(
            db,
            name=payload.name,
            code=payload.code,
            workspace_id=ws_id,
            usergroup_id=usergroup_id,
            added_by_user_id=user_id,
            is_private=bool(payload.is_private),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return mod

@routers_modules.get("", response_model=List[ModuleOut])
def list_modules(published_only: bool = Query(False), request: Request = None, db: Session = Depends(get_meta_db)):
    user_id, usergroup_id = parse_user_ctx(request)
    ws_id = resolve_workspace_id(db, usergroup_id)
    mods = module_service.list_modules(
        db,
        workspace_id=ws_id,
        user_id=user_id,
        usergroup_id=usergroup_id,
        published_only=published_only,
    )
    return mods

@routers_modules.post("/{module_id}/publish", response_model=ModuleOut)
def publish_module(module_id: int, db: Session = Depends(get_meta_db)):
    try:
        mod = module_service.publish_module(db, module_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return mod
