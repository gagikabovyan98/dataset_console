# app/services/workspace_service.py
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.meta_models import DCWorkspace

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
