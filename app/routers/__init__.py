# app/routers/__init__.py

from fastapi import APIRouter
from .core import router as core

api = APIRouter()
api.include_router(core)
