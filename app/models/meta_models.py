#  app/models/meta_models.py

from __future__ import annotations
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


SCHEMA = "dataset_console"


class DCWorkspace(Base):
    __tablename__ = "dc_workspaces"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    usergroup_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    modules: Mapped[list["DCModule"]] = relationship(
        back_populates="workspace", cascade="all,delete-orphan"
    )


class DCModule(Base):
    __tablename__ = "dc_modules"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(f"{SCHEMA}.dc_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)

    usergroup_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    added_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped["DCWorkspace"] = relationship(back_populates="modules")


class DCScript(Base):
    __tablename__ = "dc_script_store"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey(f"{SCHEMA}.dc_workspaces.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    usergroup_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    added_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DCScratchpad(Base):
    __tablename__ = "dc_scratchpad"
    __table_args__ = (
        UniqueConstraint("workspace_id", "key"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(f"{SCHEMA}.dc_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    value_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    uri: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DCArtifact(Base):
    __tablename__ = "dc_artifacts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(f"{SCHEMA}.dc_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    value_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    uri: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DCRun(Base):
    __tablename__ = "dc_runs"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey(f"{SCHEMA}.dc_workspaces.id", ondelete="SET NULL"), nullable=True
    )
    script_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    dataset_ids: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timed_out: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    stdout_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stderr_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    who_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
