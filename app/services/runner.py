# app/services/runner.py

import ast
import subprocess
import os
import base64
from __future__ import annotations
from typing import List, Optional, Set
from fastapi import HTTPException
from app.config import settings
from app.services.datasets_service import fetch_dataset_map

ALLOWED_MODULES_BASE: Set[str] = {
    "math","statistics","json","csv","itertools","functools","operator",
    "datetime","time","re","typing","collections","decimal","fractions",
    "hashlib","hmac","base64","uuid","random","pprint","warnings","logging",
    "numpy","pandas","urllib","urllib.request","http","http.client","sklearn"
}

BANNED_NAMES = {
    "open","__import__","eval","exec","compile","input","help","vars","dir",
    "globals","locals","quit","exit","getattr","setattr","delattr",
    "os","sys","pathlib","subprocess","socket","shutil","ctypes",
    "multiprocessing","selectors","importlib","builtins","inspect",
    "site","resource","signal","traceback","pkgutil"
}

BAD_OS_ATTRS = {
    "system","popen","fork","forkpty","spawnl","spawnle","spawnlp","spawnlpe",
    "spawnv","spawnve","spawnvp","spawnvpe",
    "execl","execle","execlp","execlpe","execv","execve","execvp","execvpe",
    "_exit","kill","killpg","remove","unlink","rmdir","removedirs","rename","replace","symlink"
}


def _ast_check(src: str, *, allowed_modules: Set[str]) -> None:
    try:
        tree = ast.parse(src)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Syntax error: {e}")

    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mods = []
            if isinstance(n, ast.Import):
                mods = [a.name.split(".")[0] for a in n.names]
            else:
                root = (n.module or "").split(".")[0]
                if root:
                    mods = [root]
            for m in mods:
                if m not in allowed_modules:
                    raise HTTPException(status_code=400, detail=f"Import of '{m}' is not allowed")
        if isinstance(n, ast.Name) and n.id in BANNED_NAMES:
            raise HTTPException(status_code=400, detail=f"Use of '{n.id}' is forbidden")
        if isinstance(n, ast.Attribute) and isinstance(n.attr, str) and n.attr.startswith("__"):
            raise HTTPException(status_code=400, detail="Access to dunder attributes is forbidden")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if getattr(getattr(n.func, "value", None), "id", None) == "os" and n.func.attr in BAD_OS_ATTRS:
                raise HTTPException(status_code=400, detail=f"os.{n.func.attr} is forbidden")


def _shorten(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[:limit] + f"\n\n...[truncated {len(s)-limit} bytes]"


def _base_env() -> dict:
    env = {
        "CH_HOST": settings.CH_HOST or "127.0.0.1",
        "CH_PORT": str(settings.CH_PORT or "8123"),
        "CH_USER": settings.CH_USER or "",
        "CH_PASSWORD": settings.CH_PASSWORD or "",
        "CH_SECURE": str(settings.CH_SECURE or "0"),
        "TIMEOUT_SECONDS": str(settings.TIMEOUT_SECONDS),
        "RLIMIT_CPU_SECS": str(settings.RLIMIT_CPU_SECS),
        "RLIMIT_AS_BYTES": str(settings.RLIMIT_AS_BYTES),
        "RLIMIT_FSIZE": str(settings.RLIMIT_FSIZE),
        "RLIMIT_NPROC": str(settings.RLIMIT_NPROC),
        "DATAFRAME_KIND": "pandas",
    }
    if settings.CH_DATABASE:
        env["CH_DATABASE"] = settings.CH_DATABASE

    for k in ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_SECURE"):
        v = os.getenv(k)
        if v is not None:
            env[k] = v

    for k in ("PERSIST_BUCKET", "PERSIST_PREFIX", "AUTO_UPLOAD_MINIO"):
        v = os.getenv(k)
        if v is not None:
            env[k] = v

    for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[k] = os.getenv(k, "1")
    env["MALLOC_CONF"] = os.getenv("MALLOC_CONF", "background_thread:false")
    return env


def run_script_in_docker(
    script: str,
    dataset_ids: Optional[List[int]] = None,
    *,
    extra_env: Optional[dict] = None,
    extra_allowed_imports: Optional[Set[str]] = None,
) -> dict:
    code = (script or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Empty script")
    if len(code.encode("utf-8")) > settings.MAX_SCRIPT_BYTES:
        raise HTTPException(status_code=413, detail="Script too large")

    allowed = set(ALLOWED_MODULES_BASE)
    if extra_allowed_imports:
        allowed.update(extra_allowed_imports)

    _ast_check(code, allowed_modules=allowed)

    env = _base_env()
    env["USER_CODE_B64"] = base64.b64encode(code.encode("utf-8")).decode("ascii")

    if dataset_ids:
        max_datasets = settings.MAX_DATASETS
        if len(dataset_ids) > max_datasets:
            raise HTTPException(status_code=422, detail=f"Too many datasets (max {max_datasets})")
        id_map = fetch_dataset_map(dataset_ids)
        missing = [i for i in dataset_ids if i not in id_map]
        if missing:
            raise HTTPException(
                status_code=404,
                detail={"message": "Some dataset IDs not found", "missing_ids": missing},
            )
        for idx, did in enumerate(dataset_ids, start=1):
            title, table = id_map[did]
            env[f"DATASET{idx}_ID"] = str(did)
            env[f"DATASET{idx}_TITLE"] = title
            env[f"DATASET{idx}_TABLE"] = table
        env["DATASET_COUNT"] = str(len(dataset_ids))

    if extra_env:
        env.update(extra_env)

    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--pull=never",
        "--user",
        "1000:1000",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--tmpfs",
        "/work:rw,noexec,nosuid,size=64m",
        "--tmpfs",
        "/opt/dc_modules:rw,noexec,nosuid,size=8m",
        "--workdir",
        "/work",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--network",
        "host",
        "--pids-limit",
        "128",
        "--memory",
        "512m",
        "--cpus",
        "0.5",
    ]
    for k, v in env.items():
        cmd += ["-e", f"{k}={v}"]

    image = getattr(settings, "SANDBOX_IMAGE", "dataset-console:py311-ch_v4")
    cmd += [image]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=settings.TIMEOUT_SECONDS + settings.STARTUP_OVERHEAD_SEC,
        )
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timed out", "exit_code": None, "timed_out": True}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Docker not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Docker execution error: {e}")

    return {
        "stdout": _shorten(proc.stdout.decode("utf-8", "replace"), settings.STDOUT_MAX),
        "stderr": _shorten(proc.stderr.decode("utf-8", "replace"), settings.STDERR_MAX),
        "exit_code": proc.returncode,
        "timed_out": False,
    }