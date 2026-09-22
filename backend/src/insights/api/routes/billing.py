"""``/api/billing/*``: summary, flexible consumption, prepaid credits, PAYG."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Query, Request

from insights.api.deps import get_db, resolve_range, today
from insights.store import repo

router = APIRouter(prefix="/api/billing")

GroupBy = Literal["day", "category", "instance"]
ScopeParam = Literal["org", "cluster", "appservice", "analytics"]


def _minus(a: float | None, b: float | None) -> float | None:
    if a is None:
        return None
    return round(a - (b or 0.0), 4)


@router.get("/summary")
def summary(
    request: Request,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
) -> dict[str, Any]:
    lo, hi = resolve_range(date_from, date_to, today(request))
    with get_db(request).session() as conn:
        org = repo.usage_total(conn, "org", "", lo, hi)
        attributed = repo.usage_total(conn, repo.INSTANCE_SCOPES, None, lo, hi)
        by_category = repo.usage_by_category(conn, "org", "", lo, hi)
        instances = repo.usage_by_instance(conn, repo.INSTANCE_SCOPES, lo, hi)
        names = repo.instance_names(conn)
        currency, _ = repo.billing_meta(conn)
    unit = "credits" if org.credits is not None else "currency"
    org_total = getattr(org, unit)
    by_instance = []
    for entry in instances:
        name, project = names.get(
            (entry["scope"], entry["instanceId"]), (entry["instanceId"], None)
        )
        value = entry.get(unit)
        by_instance.append(
            {
                "scope": entry["scope"],
                "instanceId": entry["instanceId"],
                "name": name,
                "projectName": project,
                "credits": entry["credits"],
                "currency": entry["currency"],
                "sharePercent": round(value / org_total * 100, 2)
                if org_total and value is not None
                else None,
            }
        )
    return {
        "from": lo.isoformat(),
        "to": hi.isoformat(),
        "currency": currency,
        "org": org.as_json(),
        "attributed": attributed.as_json(),
        "unattributed": {
            "credits": _minus(org.credits, attributed.credits),
            "currency": _minus(org.currency, attributed.currency),
        },
        "byCategory": by_category,
        "byInstance": by_instance,
    }


@router.get("/consumption")
def consumption(
    request: Request,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    group_by: GroupBy = Query("day", alias="groupBy"),
    scope: ScopeParam = "org",
) -> dict[str, Any]:
    lo, hi = resolve_range(date_from, date_to, today(request))
    scopes: list[str] = list(repo.INSTANCE_SCOPES) if scope == "org" else [scope]
    with get_db(request).session() as conn:
        if group_by == "day":
            if scope == "org":
                rows = repo.usage_by_period(conn, "org", "", lo, hi, "day")
            else:
                rows = _by_day(repo.usage_by_period(conn, scope, None, lo, hi, "day"))
        elif group_by == "category":
            target = ("org", "") if scope == "org" else (scope, None)
            rows = [
                {"key": e["category"], "credits": e["credits"], "currency": e["currency"]}
                for e in repo.usage_by_category(conn, target[0], target[1], lo, hi)
            ]
        else:
            names = repo.instance_names(conn)
            rows = [
                {
                    "key": e["instanceId"],
                    "scope": e["scope"],
                    "name": names.get((e["scope"], e["instanceId"]), (e["instanceId"], None))[0],
                    "credits": e["credits"],
                    "currency": e["currency"],
                }
                for e in repo.usage_by_instance(conn, scopes, lo, hi)
            ]
    return {
        "groupBy": group_by,
        "scope": scope,
        "from": lo.isoformat(),
        "to": hi.isoformat(),
        "rows": rows,
    }


def _by_day(series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse ``{period, category, ...}`` rows into one ``{key, credits, currency}`` per day."""
    days: dict[str, dict[str, float | None]] = {}
    for entry in series:
        slot = days.setdefault(entry["period"], {"credits": None, "currency": None})
        for unit in ("credits", "currency"):
            if entry[unit] is not None:
                slot[unit] = round((slot[unit] or 0.0) + entry[unit], 4)
    return [{"key": day, **values} for day, values in sorted(days.items())]


@router.get("/prepaid")
def prepaid(request: Request) -> dict[str, Any]:
    with get_db(request).session() as conn:
        rows = repo.list_prepaid(conn)
    credits = [
        {
            "id": r["id"],
            "creditName": r["credit_name"],
            "supportPlan": r["support_plan"],
            "startDate": r["start_date"],
            "expirationDate": r["expiration_date"],
            "total": r["total"],
            "used": r["used"],
            "remaining": r["remaining"],
            "remainingPercent": r["remaining_percent"],
        }
        for r in rows
    ]
    total = round(sum(c["total"] or 0 for c in credits), 4)
    used = round(sum(c["used"] or 0 for c in credits), 4)
    remaining = round(sum(c["remaining"] or 0 for c in credits), 4)
    return {
        "credits": credits,
        "aggregate": {
            "total": total,
            "used": used,
            "remaining": remaining,
            "remainingPercent": round(remaining / total * 100, 2) if total else None,
        },
        "fetchedAt": max((r["fetched_at"] for r in rows), default=None),
    }


@router.get("/payg")
def payg(
    request: Request,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
) -> dict[str, Any]:
    lo, hi = resolve_range(date_from, date_to, today(request))
    with get_db(request).session() as conn:
        rows = repo.list_payg(conn, lo.replace(day=1), hi)
        currency, _ = repo.billing_meta(conn)
    periods = [
        {
            "period": r["day"],
            "basic": r["basic"],
            "devPro": r["dev_pro"],
            "enterprise": r["enterprise"],
            "total": r["total"],
        }
        for r in rows
    ]
    total = {
        key: round(sum(p[key] or 0 for p in periods), 4)
        for key in ("basic", "devPro", "enterprise", "total")
    }
    return {
        "currency": next((r["currency"] for r in rows if r["currency"]), currency),
        "from": lo.isoformat(),
        "to": hi.isoformat(),
        "periods": periods,
        "total": total,
    }
