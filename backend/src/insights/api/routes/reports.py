"""``/api/reports``: list definitions and run one as JSON or CSV."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Query, Request, Response

from insights.api.deps import get_db, resolve_range, today
from insights.api.errors import ApiError
from insights.reports.registry import (
    ReportContext,
    ReportError,
    registry,
    result_to_csv,
    result_to_json,
)

router = APIRouter(prefix="/api/reports")

_RESERVED = {"from", "to", "format"}


@router.get("")
def list_reports() -> list[dict[str, Any]]:
    return [d.describe() for d in registry.list()]


@router.get("/{key}")
def run_report(
    request: Request,
    key: str,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    fmt: Literal["json", "csv"] = Query("json", alias="format"),
) -> Any:
    definition = registry.get(key)
    if definition is None:
        raise ApiError(404, "not_found", f"report '{key}' not found")
    lo, hi = resolve_range(date_from, date_to, today(request))
    extra = {k: v for k, v in request.query_params.items() if k not in _RESERVED}
    with get_db(request).session() as conn:
        ctx = ReportContext(conn=conn, date_from=lo, date_to=hi, params=extra)
        try:
            result = definition.run(ctx)
        except ReportError as exc:
            raise ApiError(400, "invalid_params", str(exc)) from exc
    if fmt == "csv":
        filename = f"{key}-{lo.isoformat()}_to_{hi.isoformat()}.csv"
        return Response(
            content=result_to_csv(result),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    return result_to_json(definition, ctx, result)
