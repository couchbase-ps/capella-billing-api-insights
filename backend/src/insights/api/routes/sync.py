"""``POST /api/sync`` and ``GET /api/sync/status``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response

from insights.api.deps import get_db, get_runner
from insights.api.errors import ApiError
from insights.store import repo
from insights.sync.runner import SyncAlreadyRunning, SyncNotConfigured

router = APIRouter(prefix="/api/sync")


@router.post("")
async def trigger_sync(request: Request, response: Response) -> dict[str, Any]:
    runner = get_runner(request)
    try:
        run_id = await runner.trigger()
    except SyncAlreadyRunning as exc:
        raise ApiError(409, "sync_running", str(exc)) from exc
    except SyncNotConfigured as exc:
        raise ApiError(409, "not_configured", str(exc)) from exc
    response.status_code = 202
    return {"runId": run_id, "status": "running"}


@router.get("/status")
def sync_status(request: Request) -> dict[str, Any]:
    with get_db(request).session() as conn:
        runs = repo.list_sync_runs(conn, limit=10)
    return {
        "running": get_runner(request).running,
        "runs": [r.as_json(include_detail=True) for r in runs],
    }
