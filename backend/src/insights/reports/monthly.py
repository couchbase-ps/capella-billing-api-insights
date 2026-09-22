"""Monthly aggregation shared by the custom reports (docs/custom-reports.md)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from insights.reports.labels import category_order, normalise_plan
from insights.reports.registry import ReportColumn, ReportContext
from insights.store import repo
from insights.sync.windows import month_end

Key = tuple[str, str]  # (scope, instance_id)


def add(cells: dict[Any, float], key: Any, value: float) -> None:
    """Accumulate keeping "has rows" semantics: a key present with 0.0 differs from absent."""
    cells[key] = round(cells.get(key, 0.0) + value, 4)


def sum_present(values: Iterable[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return round(sum(present), 4) if present else None


@dataclass
class MonthlyData:
    """Credit (or currency) figures per month, loaded once per report run."""

    unit: str
    months: list[str]
    partial_months: list[str]
    org: dict[tuple[str, str], float] = field(default_factory=dict)  # (month, category)
    instances: dict[tuple[str, Key, str], float] = field(default_factory=dict)
    seen: set[str] = field(default_factory=set)

    @property
    def categories(self) -> list[tuple[str, str]]:
        return category_order(self.seen)

    def instance_month_totals(self, month: str) -> dict[Key, dict[str, float]]:
        """``{(scope, id): {category: value}}`` for one month."""
        out: dict[Key, dict[str, float]] = {}
        for (m, key, category), value in self.instances.items():
            if m == month:
                out.setdefault(key, {})[category] = value
        return out

    def unattributed(self, month: str) -> dict[str, float]:
        """Org total minus the sum of instances per category; only non-zero cells."""
        totals: dict[str, float] = {}
        for (m, category), value in self.org.items():
            if m == month:
                add(totals, category, value)
        for (m, _key, category), value in self.instances.items():
            if m == month:
                add(totals, category, -value)
        return {c: (0.0 if v == 0 else v) for c, v in totals.items() if abs(v) > 1e-9}


def _unit_of(rows: list[repo.UsageRow]) -> str:
    if any(r.credit_spend is not None for r in rows):
        return "credits"
    return next((r.currency for r in rows if r.currency), None) or "credits"


def load_monthly(ctx: ReportContext) -> MonthlyData:
    """Read org + instance day rows for the range and bucket them per calendar month."""
    org_rows = repo.query_usage(ctx.conn, "org", "", ctx.date_from, ctx.date_to)
    inst_rows = [
        r
        for scope in repo.INSTANCE_SCOPES
        for r in repo.query_usage(ctx.conn, scope, None, ctx.date_from, ctx.date_to)
    ]
    unit = _unit_of([*org_rows, *inst_rows])

    def value(row: repo.UsageRow) -> float | None:
        return row.credit_spend if unit == "credits" else row.currency_spend

    months: set[str] = set()
    data = MonthlyData(unit=unit, months=[], partial_months=[])
    for row in org_rows:
        v = value(row)
        if v is None:
            continue
        month = row.day.isoformat()[:7]
        months.add(month)
        data.seen.add(row.category)
        add(data.org, (month, row.category), v)
    for row in inst_rows:
        v = value(row)
        if v is None:
            continue
        month = row.day.isoformat()[:7]
        months.add(month)
        data.seen.add(row.category)
        add(data.instances, (month, (row.scope, row.instance_id), row.category), v)
    data.months = sorted(months)
    data.partial_months = [
        m
        for m in data.months
        if (m == ctx.date_from.isoformat()[:7] and ctx.date_from.day != 1)
        or (m == ctx.date_to.isoformat()[:7] and ctx.date_to != month_end(ctx.date_to))
    ]
    return data


def instance_plans(ctx: ReportContext) -> dict[Key, str | None]:
    """Normalised support plan per billable instance."""
    plans: dict[Key, str | None] = {}
    for c in repo.list_clusters(ctx.conn):
        plans[("cluster", c.id)] = normalise_plan(c.support_plan)
    for a in repo.list_analytics_clusters(ctx.conn):
        plans[("analytics", a.id)] = normalise_plan(a.support_plan)
    for s in repo.list_app_services(ctx.conn):
        plans[("appservice", s.id)] = normalise_plan(s.plan)
    return plans


def value_type(unit: str) -> str:
    return "credits" if unit == "credits" else "currency"


def category_columns(data: MonthlyData) -> list[ReportColumn]:
    kind = value_type(data.unit)
    return [ReportColumn(code, label, kind) for code, label in data.categories]  # type: ignore[arg-type]


def total_row(columns: list[ReportColumn], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum every numeric column; the first column reads ``Total``, other labels are null."""
    totals: dict[str, Any] = {}
    numeric = {"number", "credits", "currency"}
    for i, column in enumerate(columns):
        if column.type in numeric:
            totals[column.key] = sum_present(r.get(column.key) for r in rows)
        else:
            totals[column.key] = "Total" if i == 0 else None
    return totals


def base_meta(data: MonthlyData) -> dict[str, Any]:
    return {
        "unit": data.unit,
        "categoryOrder": [label for _, label in data.categories],
        "partialMonths": data.partial_months,
    }


def month_bounds(months: list[str]) -> tuple[date, date] | None:
    if not months:
        return None
    first = date.fromisoformat(f"{months[0]}-01")
    last = month_end(date.fromisoformat(f"{months[-1]}-01"))
    return first, last
