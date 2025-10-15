# app/routers/__init__.py

from fastapi import APIRouter

from .core import router as core
from .scratchpad import router as scratchpad
from .modules import ws_router as ws_modules
from .workspaces import router as workspaces
from .scripts import router as scripts


api = APIRouter()
api.include_router(core)
api.include_router(scratchpad)
api.include_router(ws_modules)
api.include_router(workspaces)
api.include_router(scripts)
