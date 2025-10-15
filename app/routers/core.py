# app/routers/core.py

import json, zlib, base64

from fastapi import APIRouter, Query, Body, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import text, select
from typing import List, Optional
from app.services.scaffold import build_scaffold_code
from app.services.datasets_service import fetch_dataset_map, get_pg_engine
from app.services.script_store_service import get_script
from app.services.runner import run_script_in_docker
from app.services import module_service
from app.services.db import SessionLocal
from app.services.workspace_service import resolve_workspace_id
from app.models.meta_models import DCWorkspace


router = APIRouter()

@router.get("/healthz")
def healthz():
    pg_ok = True
    try:
        eng = get_pg_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pg_ok = False
    return {"ok": True, "postgres_ok": pg_ok}

@router.get("/dataset_scaffold", response_class=PlainTextResponse)
def dataset_scaffold(
    ids: List[int] = Query(..., description="Dataset IDs: ?ids=1&ids=2"),
    default_limit: int = Query(1000, ge=1, le=1_000_000),
):
    id_map = fetch_dataset_map(ids)
    missing = [i for i in ids if i not in id_map]
    if missing:
        raise HTTPException(
            status_code=404,
            detail={"message": "Some dataset IDs not found in PostgreSQL", "missing_ids": missing},
        )
    pairs = [id_map[i] for i in ids]
    code = build_scaffold_code(pairs, default_limit=default_limit)
    return PlainTextResponse(content=code, media_type="text/x-python")

class ScriptCreate(BaseModel):
    name: str
    code: str
    meta: Optional[dict] = None

class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    meta: Optional[dict] = None

class ExecReq(BaseModel):
    script: Optional[str] = None
    script_id: Optional[int] = None
    dataset_ids: List[int] = []
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None

@router.post("/exec_script")
def exec_script(payload: ExecReq = Body(...)):
    # Resolve code
    code: str | None = None
    if payload.script_id is not None:
        row = get_script(payload.script_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"script_id={payload.script_id} not found")
        code = (row.get("code") or "").strip()
    else:
        code = (payload.script or "").strip()

    if not code:
        raise HTTPException(status_code=400, detail="No script provided")

    # Resolve workspace
    with SessionLocal() as s:
        ws_id: int | None = None
        if payload.workspace_id:
            ws = s.get(DCWorkspace, payload.workspace_id)
            if not ws:
                raise HTTPException(status_code=404, detail="workspace not found")
            ws_id = ws.id
        elif payload.workspace_name:
            ws = s.scalar(select(DCWorkspace).where(DCWorkspace.name == payload.workspace_name))
            if not ws:
                ws = DCWorkspace(name=payload.workspace_name)
                s.add(ws); s.commit(); s.refresh(ws)
            ws_id = ws.id
        else:
            ws_id = resolve_workspace_id(s, None)

        mods = module_service.list_modules(
            s,
            workspace_id=ws_id,
            user_id=None,
            usergroup_id=None,
            published_only=True,
        )

        extra_env = {}
        allowed_names = set()
        if mods:
            payload_map = {m.name: m.code for m in mods}
            raw = json.dumps(payload_map).encode("utf-8")
            dc_modules_b64 = base64.b64encode(zlib.compress(raw, 6)).decode("ascii")
            extra_env["DC_MODULES_B64"] = dc_modules_b64
            allowed_names = set(payload_map.keys())

    return run_script_in_docker(
        script=code,
        dataset_ids=payload.dataset_ids or [],
        extra_env=extra_env,
        extra_allowed_imports=allowed_names,
    )