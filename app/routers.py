# app/routers.py
from fastapi import APIRouter, Query, Body, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text

from app.services.scaffold import build_scaffold_code
from app.services.datasets_service import fetch_dataset_map, get_pg_engine

# scripts store
from app.services.script_store_service import create_script, update_script, get_script, list_scripts

# runner + modules + meta DB
from app.services.runner import run_script_in_docker
from app.services import module_service
from app.services.meta_db import SessionLocal

from app.utils.auth import parse_user_ctx
from app.services.workspace_service import resolve_workspace_id

import json, zlib, base64

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


@router.post("/exec_script")
def exec_script(
    request: Request,
    payload: ExecReq = Body(...),
):
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

    # user/group → workspace, собрать опубликованные и доступные модули
    user_id, usergroup_id = parse_user_ctx(request)

    extra_env = {}
    allowed_names = set()

    with SessionLocal() as s:
        ws_id = resolve_workspace_id(s, usergroup_id)
        mods = module_service.list_modules(
            s,
            workspace_id=ws_id,
            user_id=user_id,
            usergroup_id=usergroup_id,
            published_only=True,
        )
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


@router.post("/scripts")
def scripts_create(payload: ScriptCreate):
    sid = create_script(payload.name, payload.code, payload.meta)
    return {"id": sid}


@router.get("/scripts")
def scripts_list(limit: int = 100):
    return {"items": list_scripts(limit=limit)}


@router.get("/scripts/{script_id}")
def scripts_get(script_id: int):
    row = get_script(script_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return row


@router.patch("/scripts/{script_id}")
def scripts_update(script_id: int, payload: ScriptUpdate):
    if payload.name is None and payload.code is None and payload.meta is None:
        return {"ok": True, "updated": False}
    update_script(script_id, payload.name, payload.code, payload.meta)
    return {"ok": True, "updated": True}
