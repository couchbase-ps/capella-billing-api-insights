"""``GET /health`` and ``GET /api/organization``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from insights.api.deps import get_db, get_settings
from insights.api.errors import ApiError
from insights.store import repo

router = APIRouter()


def _last_sync(request: Request) -> dict[str, Any] | None:
    with get_db(request).session() as conn:
        run = repo.last_sync_run(conn)
    return run.as_json() if run else None


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    settings = get_settings(request)
    return {
        "status": "ok",
        "mock": settings.capella_mock,
        "configured": settings.configured,
        "lastSync": _last_sync(request),
    }


@router.get("/api/organization")
def organization(request: Request) -> dict[str, Any]:
    with get_db(request).session() as conn:
        row = repo.get_organization(conn)
        if row is None:
            raise ApiError(404, "not_synced", "no organization synced yet; run a sync first")
        counts = repo.count_inventory(conn)
        currency, mode = repo.billing_meta(conn)
        run = repo.last_sync_run(conn)
    return {
        "id": row["id"],
        "name": row["name"],
        "billingCurrency": currency,
        "billingMode": mode,
        "counts": counts,
        "lastSync": run.as_json() if run else None,
    }
