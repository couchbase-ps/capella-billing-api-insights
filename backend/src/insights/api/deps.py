"""Dependency helpers reading shared objects from ``app.state``."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import Request

from insights.api.errors import ApiError
from insights.config import Settings
from insights.store.db import Database
from insights.sync.runner import SyncRunner


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_runner(request: Request) -> SyncRunner:
    return request.app.state.runner


def today(request: Request) -> date:
    """Current UTC date; tests may pin ``app.state.today``."""
    pinned = getattr(request.app.state, "today", None)
    return pinned() if callable(pinned) else datetime.now(UTC).date()


def resolve_range(date_from: date | None, date_to: date | None, now: date) -> tuple[date, date]:
    """Apply the contract default (last 30 full days ending yesterday) and validate order."""
    hi = date_to or (now - timedelta(days=1))
    lo = date_from or (hi - timedelta(days=29))
    if hi < lo:
        raise ApiError(400, "invalid_range", f"'to' ({hi}) is before 'from' ({lo})")
    return lo, hi
