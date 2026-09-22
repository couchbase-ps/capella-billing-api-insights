"""The owner's custom monthly credit reports (docs/custom-reports.md).

* ``credits-by-category`` - org-level month x category rows.
* ``credits-by-plan``     - month x support plan, categories transposed, Unattributed remainder.
* ``credits-by-cluster``  - month x instance (App Services folded into their cluster), plan
  totals and a proportional-by-plan on-demand estimate from pay-as-you-go periods.
"""

from __future__ import annotations

from typing import Any

from insights.reports.labels import PLAN_ORDER, UNATTRIBUTED, plan_sort_key
from insights.reports.monthly import (
    Key,
    MonthlyData,
    add,
    base_meta,
    category_columns,
    instance_plans,
    load_monthly,
    month_bounds,
    sum_present,
    total_row,
    value_type,
)
from insights.reports.registry import (
    ReportColumn,
    ReportContext,
    ReportDefinition,
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

_PAYG_FIELD = {"Basic": "basic", "Developer Pro": "dev_pro", "Enterprise": "enterprise"}
_TOTAL_PLAN_COLUMN = {
    "Developer Pro": ("totalDevPro", "Total Plan Developer Pro"),
    "Enterprise": ("totalEnterprise", "Total Plan Enterprise"),
    "Basic": ("totalBasic", "Total Plan Basic"),
}


def _row_total(row: dict[str, Any], data: MonthlyData) -> float | None:
    return sum_present(row.get(code) for code, _ in data.categories)


# --- report 1 ---------------------------------------------------------------------------


def credits_by_category(ctx: ReportContext) -> ReportResult:
    """One row per month x category (org scope), fixed category order, Total row."""
    data = load_monthly(ctx)
    columns = [
        ReportColumn("month", "Month", "month"),
        ReportColumn("category", "Row Labels", "string"),
        ReportColumn("credits", "Sum of consumed Credits", value_type(data.unit)),  # type: ignore[arg-type]
    ]
    rows = [
        {"month": month, "category": label, "credits": data.org[(month, code)]}
        for month in data.months
        for code, label in data.categories
        if (month, code) in data.org
    ]
    return ReportResult(columns, rows, total_row(columns, rows), base_meta(data))


# --- report 2 ---------------------------------------------------------------------------


def credits_by_plan(ctx: ReportContext) -> ReportResult:
    """Month x support plan with one column per category and a Grand Total."""
    data = load_monthly(ctx)
    plans = instance_plans(ctx)
    columns = [
        ReportColumn("month", "Month", "month"),
        ReportColumn("plan", "Credit Plan", "string"),
        *category_columns(data),
        ReportColumn("grandTotal", "Grand Total", value_type(data.unit)),  # type: ignore[arg-type]
    ]
    rows: list[dict[str, Any]] = []
    for month in data.months:
        per_plan: dict[str, dict[str, float]] = {}
        for key, cells in data.instance_month_totals(month).items():
            plan = plans.get(key) or "Unknown"
            bucket = per_plan.setdefault(plan, {})
            for category, value in cells.items():
                add(bucket, category, value)
        remainder = data.unattributed(month)
        if remainder:
            per_plan[UNATTRIBUTED] = remainder
        for plan in sorted(per_plan, key=plan_sort_key):
            row: dict[str, Any] = {"month": month, "plan": plan}
            for code, _ in data.categories:
                row[code] = per_plan[plan].get(code)
            row["grandTotal"] = _row_total(row, data)
            rows.append(row)
    return ReportResult(columns, rows, total_row(columns, rows), base_meta(data))


# --- report 3 ---------------------------------------------------------------------------


def _row_targets(ctx: ReportContext) -> tuple[dict[Key, Key], dict[Key, str]]:
    """Map each billable instance to its report row (App Services fold into their cluster)."""
    target: dict[Key, Key] = {}
    names: dict[Key, str] = {}
    clusters = {c.id: c for c in repo.list_clusters(ctx.conn)}
    for c in clusters.values():
        target[("cluster", c.id)] = ("cluster", c.id)
        names[("cluster", c.id)] = c.name
    for a in repo.list_analytics_clusters(ctx.conn):
        target[("analytics", a.id)] = ("analytics", a.id)
        names[("analytics", a.id)] = a.name
    for s in repo.list_app_services(ctx.conn):
        own = ("appservice", s.id)
        target[own] = ("cluster", s.cluster_id) if s.cluster_id in clusters else own
        names[own] = s.name
    return target, names


def _payg_ratios(
    ctx: ReportContext, data: MonthlyData, plan_totals: dict[tuple[str, str], float]
) -> dict[tuple[str, str], float | None]:
    """``(month, plan) -> min(1, payg / spend)``; missing when the month has no PAYG rows."""
    bounds = month_bounds(data.months)
    if bounds is None:
        return {}
    payg: dict[str, dict[str, float]] = {}
    for row in repo.list_payg(ctx.conn, bounds[0], bounds[1]):
        month = str(row["day"])[:7]
        slot = payg.setdefault(month, {})
        for plan, column in _PAYG_FIELD.items():
            slot[plan] = slot.get(plan, 0.0) + (row[column] or 0.0)
    ratios: dict[tuple[str, str], float | None] = {}
    for (month, plan), spend in plan_totals.items():
        if month not in payg or plan not in _PAYG_FIELD or spend <= 0:
            ratios[(month, plan)] = None
        else:
            ratios[(month, plan)] = min(1.0, payg[month].get(plan, 0.0) / spend)
    return ratios


def credits_by_cluster(ctx: ReportContext) -> ReportResult:
    """Month x instance rows, plan totals and the proportional-by-plan on-demand estimate."""
    data = load_monthly(ctx)
    plans = instance_plans(ctx)
    target, names = _row_targets(ctx)

    rows: list[dict[str, Any]] = []
    plan_totals: dict[tuple[str, str], float] = {}
    for month in data.months:
        cells_by_row: dict[Key, dict[str, float]] = {}
        for key, cells in data.instance_month_totals(month).items():
            row_key = target.get(key, key)
            bucket = cells_by_row.setdefault(row_key, {})
            for category, value in cells.items():
                add(bucket, category, value)
        entries = sorted(cells_by_row.items(), key=lambda kv: names.get(kv[0], kv[0][1]).lower())
        remainder = data.unattributed(month)
        if remainder:
            entries.append((("org", ""), remainder))
        for row_key, cells in entries:
            is_unattributed = row_key == ("org", "")
            plan = None if is_unattributed else plans.get(row_key)
            row: dict[str, Any] = {
                "month": month,
                "instance": UNATTRIBUTED if is_unattributed else names.get(row_key, row_key[1]),
                "plan": plan,
            }
            for code, _ in data.categories:
                row[code] = cells.get(code)
            total = _row_total(row, data)
            row["_total"] = total
            rows.append(row)
            if plan and total is not None:
                add(plan_totals, (month, plan), total)

    ratios = _payg_ratios(ctx, data, plan_totals)
    seen_plans = {r["plan"] for r in rows if r["plan"]}
    plan_columns = [
        ReportColumn(*_TOTAL_PLAN_COLUMN[p], value_type(data.unit))  # type: ignore[arg-type]
        for p in ("Developer Pro", "Enterprise", "Basic")
        if p != "Basic" or "Basic" in seen_plans
    ]
    for row in rows:
        total = row.pop("_total")
        plan = row.pop("plan")
        for p in PLAN_ORDER:
            key, _ = _TOTAL_PLAN_COLUMN[p]
            if p != "Basic" or "Basic" in seen_plans:
                row[key] = total if plan == p else None
        ratio = ratios.get((row["month"], plan)) if plan else None
        row["onDemand"] = (
            round(total * ratio, 4) if ratio is not None and total is not None else None
        )

    columns = [
        ReportColumn("month", "Month", "month"),
        ReportColumn("instance", "Cluster Instance Name", "string"),
        *category_columns(data),
        *plan_columns,
        ReportColumn("onDemand", "Total On-demand Credits", value_type(data.unit)),  # type: ignore[arg-type]
    ]
    meta = {**base_meta(data), "onDemandMethod": "proportional-by-plan"}
    return ReportResult(columns, rows, total_row(columns, rows), meta)


def register_custom(target: ReportRegistry = registry) -> None:
    """Register the three custom monthly reports (idempotent)."""
    target.register(
        ReportDefinition(
            key="credits-by-category",
            title="Credits split up by categories",
            description="Org-level credits per month and billing category.",
            params=_RANGE_PARAMS,
            run=credits_by_category,
        )
    )
    target.register(
        ReportDefinition(
            key="credits-by-plan",
            title="Credits by plan",
            description="Credits per month and support plan, one column per category.",
            params=_RANGE_PARAMS,
            run=credits_by_plan,
        )
    )
    target.register(
        ReportDefinition(
            key="credits-by-cluster",
            title="Credits by usage per cluster",
            description="Credits per month and cluster with plan totals and on-demand estimate.",
            params=_RANGE_PARAMS,
            run=credits_by_cluster,
        )
    )
