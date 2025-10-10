# app/main.py

from contextlib import asynccontextmanager
import asyncio
import os
import subprocess

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import router
from app.routers_scratchpad import scratchpad_router
from app.routers_modules import routers_modules
from app.services.meta_init import init_meta_db



def _warmup_sandbox_image():
    image = os.getenv("SANDBOX_IMAGE", "dataset-console:py311-ch_v4")
    try:
        subprocess.run(
            ["docker", "pull", image],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

    try:
        subprocess.run(
            [
                "docker", "run", "--rm", "-i", "--pull=never",
                "--user", "1000:1000",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                "--tmpfs", "/work:rw,noexec,nosuid,size=16m",
                "--workdir", "/work",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges:true",
                "--network", "host",
                "--pids-limit", "32",
                "--memory", "128m",
                "--memory-swap", "128m",
                "--cpus", "0.25",
                image,
            ],
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(_warmup_sandbox_image)
    # ORM create_all и сид дефолтного воркспейса
    await asyncio.to_thread(init_meta_db)
    yield


app = FastAPI(title="Dataset Console", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
app.include_router(scratchpad_router)
app.include_router(routers_modules)
