"""Built-in reports: ``consumption-summary`` and ``cluster-daily``."""

from __future__ import annotations

from typing import Any

from insights.reports.registry import (
    ReportColumn,
    ReportContext,
    ReportDefinition,
    ReportError,
    ReportParam,
    ReportRegistry,
    ReportResult,
    registry,
)
from insights.store import repo

_RANGE_PARAMS = (
    ReportParam("from", "date", True, "First day (inclusive)"),
    ReportParam("to", "date", True, "Last day (inclusive)"),
)


def _sum(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return round(sum(present), 4) if present else None


def consumption_summary(ctx: ReportContext) -> ReportResult:
    """One row per instance x category over the range, every scope included."""
    names = repo.instance_names(ctx.conn)
    rows: list[dict[str, Any]] = []
    for scope in repo.INSTANCE_SCOPES:
        totals: dict[tuple[str, str], repo.Money] = {}
        for usage in repo.query_usage(ctx.conn, scope, None, ctx.date_from, ctx.date_to):
            key = (usage.instance_id, usage.category)
            prev = totals.get(key, repo.Money(None, None))
            totals[key] = repo.Money(
                _sum([prev.credits, usage.credit_spend]),
                _sum([prev.currency, usage.currency_spend]),
            )
        for (instance_id, category), money in totals.items():
            name, project = names.get((scope, instance_id), (instance_id, None))
            rows.append(
                {
                    "scope": scope,
                    "instanceId": instance_id,
                    "name": name,
                    "project": project,
                    "category": category,
                    "credits": money.credits,
                    "currency": money.currency,
                }
            )
    rows.sort(key=lambda r: (-(r["credits"] or r["currency"] or 0), r["name"], r["category"]))
    return ReportResult(
        columns=[
            ReportColumn("scope", "Scope", "string"),
            ReportColumn("instanceId", "Instance ID", "string"),
            ReportColumn("name", "Name", "string"),
            ReportColumn("project", "Project", "string"),
            ReportColumn("category", "Category", "string"),
            ReportColumn("credits", "Credits", "credits"),
            ReportColumn("currency", "Currency", "currency"),
        ],
        rows=rows,
        totals={
            "credits": _sum([r["credits"] for r in rows]),
            "currency": _sum([r["currency"] for r in rows]),
        },
    )


def _resolve_scope(ctx: ReportContext, instance_id: str) -> tuple[str, str]:
    if repo.get_cluster(ctx.conn, instance_id):
        return "cluster", repo.get_cluster(ctx.conn, instance_id).name  # type: ignore[union-attr]
    analytics = repo.get_analytics_cluster(ctx.conn, instance_id)
    if analytics:
        return "analytics", analytics.name
    service = repo.get_app_service(ctx.conn, instance_id)
    if service:
        return "appservice", service.name
    raise ReportError(f"unknown cluster id '{instance_id}'")


def cluster_daily(ctx: ReportContext) -> ReportResult:
    """One row per day x category for one operational or Analytics cluster."""
    instance_id = ctx.require("clusterId")
    scope, name = _resolve_scope(ctx, instance_id)
    rows = [
        {
            "day": u.day.isoformat(),
            "cluster": name,
            "scope": scope,
            "category": u.category,
            "credits": u.credit_spend,
            "currency": u.currency_spend,
        }
        for u in repo.query_usage(ctx.conn, scope, instance_id, ctx.date_from, ctx.date_to)
    ]
    return ReportResult(
        columns=[
            ReportColumn("day", "Day", "date"),
            ReportColumn("cluster", "Cluster", "string"),
            ReportColumn("scope", "Scope", "string"),
            ReportColumn("category", "Category", "string"),
            ReportColumn("credits", "Credits", "credits"),
            ReportColumn("currency", "Currency", "currency"),
        ],
        rows=rows,
        totals={
            "credits": _sum([r["credits"] for r in rows]),
            "currency": _sum([r["currency"] for r in rows]),
        },
    )


def register_builtin(target: ReportRegistry = registry) -> None:
    """Register the built-in reports (idempotent)."""
    target.register(
        ReportDefinition(
            key="consumption-summary",
            title="Consumption summary",
            description="Credits per instance and category over the range, all scopes.",
            params=_RANGE_PARAMS,
            run=consumption_summary,
        )
    )
    target.register(
        ReportDefinition(
            key="cluster-daily",
            title="Cluster daily consumption",
            description="Daily credits per category for one operational or Analytics cluster.",
            params=(
                *_RANGE_PARAMS,
                ReportParam("clusterId", "string", True, "Operational or Analytics cluster id"),
            ),
            run=cluster_daily,
        )
    )
