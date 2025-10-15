# app/services/workspace_service.py

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.meta_models import DCWorkspace, DCModule, DCScratchpad, DCArtifact

def resolve_workspace_id(db: Session, usergroup_id: int | None) -> int:
    if not usergroup_id:
        ws = db.execute(select(DCWorkspace).where(DCWorkspace.name == "default")).scalar_one_or_none()
        if not ws:
            obj = DCWorkspace(name="default", usergroup_id=None)
            db.add(obj); db.commit(); db.refresh(obj)
            return obj.id
        return ws.id
    name = f"ws_{usergroup_id}"
    ws = db.execute(select(DCWorkspace).where(DCWorkspace.name == name)).scalar_one_or_none()
    if not ws:
        obj = DCWorkspace(name=name, usergroup_id=usergroup_id)
        db.add(obj); db.commit(); db.refresh(obj)
        return obj.id
    return ws.id

def create_workspace(db: Session, name: str, usergroup_id: int | None = None) -> DCWorkspace:
    exists = db.execute(select(DCWorkspace).where(DCWorkspace.name == name)).scalar_one_or_none()
    if exists:
        raise ValueError("Workspace with this name already exists")
    ws = DCWorkspace(name=name, usergroup_id=usergroup_id)
    db.add(ws); db.commit(); db.refresh(ws)
    return ws

def list_workspaces(db: Session) -> list[DCWorkspace]:
    rows = db.execute(select(DCWorkspace).order_by(DCWorkspace.created_at.desc())).scalars().all()
    return list(rows)

def delete_workspace(db: Session, workspace_id: int) -> int:
    ws = db.get(DCWorkspace, workspace_id)
    if not ws:
        return 0
    db.delete(ws)
    db.commit()
    return 1

def get_workspace_stats(db: Session, workspace_id: int) -> dict:
    mods = db.scalar(select(func.count(DCModule.id)).where(DCModule.workspace_id == workspace_id)) or 0
    pads = db.scalar(select(func.count(DCScratchpad.id)).where(DCScratchpad.workspace_id == workspace_id)) or 0
    arts = db.scalar(select(func.count(DCArtifact.id)).where(DCArtifact.workspace_id == workspace_id)) or 0
    return {"modules": mods, "scratchpads": pads, "artifacts": arts}
