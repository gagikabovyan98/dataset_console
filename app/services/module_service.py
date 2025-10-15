# app/services/module_service.py

from __future__ import annotations
import re, ast
from typing import List, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, select
from app.models.meta_models import DCModule, DCWorkspace

_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

def _validate_module_name(name: str) -> None:
    if not _NAME_RE.match(name or ""):
        raise ValueError("Invalid module name. Use [A-Za-z_][A-Za-z0-9_]{0,63}.")

def _fast_ast_check(code: str) -> None:
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error: {e}")

def get_default_workspace_id(db: Session) -> int:
    ws = db.execute(select(DCWorkspace).where(DCWorkspace.name == "default")).scalar_one_or_none()
    if ws is None:
        obj = DCWorkspace(name="default", usergroup_id=None)
        db.add(obj); db.commit(); db.refresh(obj)
        return obj.id
    return ws.id

def save_or_update_draft(
    db: Session,
    *,
    name: str,
    code: str,
    workspace_id: int,
    usergroup_id: Optional[int],
    added_by_user_id: Optional[int],
    is_private: bool = False,
) -> DCModule:
    _validate_module_name(name)
    _fast_ast_check(code)

    existing = db.execute(
        select(DCModule).where(
            DCModule.workspace_id == workspace_id,
            DCModule.name == name,
        )
    ).scalar_one_or_none()

    if existing:
        existing.code = code
        existing.usergroup_id = usergroup_id
        existing.added_by_user_id = added_by_user_id
        existing.is_private = bool(is_private)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    mod = DCModule(
        workspace_id=workspace_id,
        name=name,
        code=code,
        usergroup_id=usergroup_id,
        added_by_user_id=added_by_user_id,
        is_private=bool(is_private),
        is_published=False,
    )
    db.add(mod)
    db.commit()
    db.refresh(mod)
    return mod

def list_modules(
    db: Session,
    *,
    workspace_id: int,
    user_id: Optional[int],
    usergroup_id: Optional[int],
    published_only: bool = False,
) -> List[DCModule]:

    stmt = select(DCModule).where(DCModule.workspace_id == workspace_id)

    if published_only:
        stmt = stmt.where(DCModule.is_published.is_(True))

    public_cond = DCModule.is_private.is_(False)

    private_checks = []
    if user_id is not None:
        private_checks.append(DCModule.added_by_user_id == user_id)
    if usergroup_id is not None:
        private_checks.append(DCModule.usergroup_id == usergroup_id)

    if private_checks:
        private_cond = and_(DCModule.is_private.is_(True), or_(*private_checks))
        visibility_cond = or_(public_cond, private_cond)
    else:
        visibility_cond = public_cond

    stmt = stmt.where(visibility_cond)

    return db.execute(stmt).scalars().all()

def get_module(db: Session, module_id: int) -> DCModule | None:
    return db.execute(select(DCModule).where(DCModule.id == module_id)).scalar_one_or_none()

def publish_module(db: Session, module_id: int) -> DCModule:
    from datetime import datetime, timezone
    mod = get_module(db, module_id)
    if not mod:
        raise ValueError("Module not found")
    mod.is_published = True
    mod.published_at = datetime.now(timezone.utc)
    db.add(mod)
    db.commit()
    db.refresh(mod)
    return mod

def delete_module(db: Session, module_id: int) -> int:
    obj = db.get(DCModule, module_id)
    if not obj:
        return 0
    db.delete(obj)
    db.commit()
    return 1
