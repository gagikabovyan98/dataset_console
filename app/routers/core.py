# app/routers/core.py

from __future__ import annotations
import json, zlib, base64
from typing import Optional, Dict, List

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field
from app.services.runner import run_script_in_docker

router = APIRouter()

class DatasetItem(BaseModel):
    id: int
    title: str
    ch_table: str

class ExecPrepared(BaseModel):
    script: str = Field(..., min_length=1)
    modules_map: Optional[Dict[str, str]] = None
    datasets: Optional[List[DatasetItem]] = None
    extra_env: Optional[Dict[str, str]] = None

@router.get("/healthz")
def healthz():
    return {"ok": True}

@router.post("/exec_script")
def exec_script(payload: ExecPrepared = Body(...)):
    code = (payload.script or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="No script provided")

    extra_env: Dict[str, str] = dict(payload.extra_env or {})
    allowed_names = set()

    # Упаковать кастом-модули (если прислали)
    if payload.modules_map:
        raw = json.dumps(payload.modules_map).encode("utf-8")
        dc_modules_b64 = base64.b64encode(zlib.compress(raw, 6)).decode("ascii")
        extra_env["DC_MODULES_B64"] = dc_modules_b64
        allowed_names = set(payload.modules_map.keys())

    # Датасеты — только разложить в ENV (без БД)
    dataset_ids: List[int] = []
    if payload.datasets:
        for idx, d in enumerate(payload.datasets, start=1):
            extra_env[f"DATASET{idx}_ID"] = str(d.id)
            extra_env[f"DATASET{idx}_TITLE"] = d.title
            extra_env[f"DATASET{idx}_TABLE"] = d.ch_table
            dataset_ids.append(d.id)
        extra_env["DATASET_COUNT"] = str(len(payload.datasets))

    return run_script_in_docker(
        script=code,
        dataset_ids=dataset_ids,
        extra_env=extra_env,
        extra_allowed_imports=allowed_names,
    )