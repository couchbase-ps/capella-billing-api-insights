"""Billing repositories: credit usage rows, prepaid credits and pay-as-you-go periods."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from insights.capella.models import PayAsYouGoPeriod, PrepaidCredit

Scope = Literal["org", "cluster", "appservice", "analytics"]
INSTANCE_SCOPES: tuple[str, ...] = ("cluster", "appservice", "analytics")


@dataclass(frozen=True)
class UsageRow:
    """One (day, scope, instance, category) figure. Credits and currency are independent."""

    day: date
    scope: str
    instance_id: str
    category: str
    credit_spend: float | None
    currency_spend: float | None
    currency: str | None


@dataclass(frozen=True)
class Money:
    credits: float | None
    currency: float | None

    def as_json(self) -> dict[str, float | None]:
        return {"credits": self.credits, "currency": self.currency}


def _money(row: sqlite3.Row) -> Money:
    return Money(_num(row["credits"]), _num(row["currency"]))


def _num(value: Any) -> float | None:
    return None if value is None else round(float(value), 4)


# --- credit usage -----------------------------------------------------------------------


def replace_credit_usage(
    conn: sqlite3.Connection,
    scope: str,
    instance_id: str,
    day_from: date,
    day_to: date,
    rows: Iterable[UsageRow],
    fetched_at: str,
) -> int:
    """Replace every row of ``scope``/``instance_id`` inside ``[day_from, day_to]``.

    Rows outside the window (other months, other instances) are untouched, so Capella's late
    corrections for a re-fetched window win without losing older history.
    """
    conn.execute(
        "DELETE FROM credit_usage WHERE scope = ? AND instance_id = ? AND day BETWEEN ? AND ?",
        (scope, instance_id, day_from.isoformat(), day_to.isoformat()),
    )
    payload = [
        (
            r.day.isoformat(),
            r.scope,
            r.instance_id,
            r.category,
            r.credit_spend,
            r.currency_spend,
            r.currency,
            fetched_at,
        )
        for r in rows
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO credit_usage (day, scope, instance_id, category, credit_spend,"
        " currency_spend, currency, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        payload,
    )
    return len(payload)


def _where(
    scope: str | Sequence[str], instance_id: str | None, lo: date, hi: date
) -> tuple[str, list[Any]]:
    scopes = [scope] if isinstance(scope, str) else list(scope)
    clause = f"scope IN ({','.join('?' for _ in scopes)}) AND day BETWEEN ? AND ?"
    params: list[Any] = [*scopes, lo.isoformat(), hi.isoformat()]
    if instance_id is not None:
        clause += " AND instance_id = ?"
        params.append(instance_id)
    return clause, params


def query_usage(
    conn: sqlite3.Connection, scope: str, instance_id: str | None, lo: date, hi: date
) -> list[UsageRow]:
    """Raw daily rows for a scope (optionally one instance) inside ``[lo, hi]``."""
    clause, params = _where(scope, instance_id, lo, hi)
    rows = conn.execute(
        f"SELECT * FROM credit_usage WHERE {clause} ORDER BY day, instance_id, category", params
    ).fetchall()
    return [
        UsageRow(
            day=date.fromisoformat(r["day"]),
            scope=r["scope"],
            instance_id=r["instance_id"],
            category=r["category"],
            credit_spend=_num(r["credit_spend"]),
            currency_spend=_num(r["currency_spend"]),
            currency=r["currency"],
        )
        for r in rows
    ]


def usage_by_period(
    conn: sqlite3.Connection,
    scope: str,
    instance_id: str | None,
    lo: date,
    hi: date,
    granularity: Literal["day", "month"] = "day",
) -> list[dict[str, Any]]:
    """``[{period, category, credits, currency}]`` summed per day or per month."""
    clause, params = _where(scope, instance_id, lo, hi)
    period = "day" if granularity == "day" else "substr(day, 1, 7)"
    rows = conn.execute(
        f"SELECT {period} AS period, category, SUM(credit_spend) AS credits,"
        f" SUM(currency_spend) AS currency FROM credit_usage WHERE {clause}"
        " GROUP BY period, category ORDER BY period, category",
        params,
    ).fetchall()
    return [{"period": r["period"], "category": r["category"], **_money(r).as_json()} for r in rows]


def usage_by_category(
    conn: sqlite3.Connection,
    scope: str | Sequence[str],
    instance_id: str | None,
    lo: date,
    hi: date,
) -> list[dict[str, Any]]:
    """``[{category, credits, currency, contributionPercent}]`` over the range."""
    clause, params = _where(scope, instance_id, lo, hi)
    rows = conn.execute(
        f"SELECT category, SUM(credit_spend) AS credits, SUM(currency_spend) AS currency"
        f" FROM credit_usage WHERE {clause} GROUP BY category ORDER BY credits DESC, category",
        params,
    ).fetchall()
    entries = [{"category": r["category"], **_money(r).as_json()} for r in rows]
    return with_percent(entries, "contributionPercent")


def usage_total(
    conn: sqlite3.Connection,
    scope: str | Sequence[str],
    instance_id: str | None,
    lo: date,
    hi: date,
) -> Money:
    clause, params = _where(scope, instance_id, lo, hi)
    row = conn.execute(
        f"SELECT SUM(credit_spend) AS credits, SUM(currency_spend) AS currency"
        f" FROM credit_usage WHERE {clause}",
        params,
    ).fetchone()
    return _money(row)


def usage_by_instance(
    conn: sqlite3.Connection, scopes: Sequence[str], lo: date, hi: date
) -> list[dict[str, Any]]:
    """``[{scope, instanceId, credits, currency}]`` for every instance with rows in range."""
    clause, params = _where(scopes, None, lo, hi)
    rows = conn.execute(
        f"SELECT scope, instance_id, SUM(credit_spend) AS credits, SUM(currency_spend) AS currency"
        f" FROM credit_usage WHERE {clause} GROUP BY scope, instance_id"
        " ORDER BY credits DESC, currency DESC, instance_id",
        params,
    ).fetchall()
    return [
        {"scope": r["scope"], "instanceId": r["instance_id"], **_money(r).as_json()} for r in rows
    ]


def credits_per_instance(
    conn: sqlite3.Connection, scope: str, lo: date, hi: date
) -> dict[str, Money]:
    """Totals per instance for card figures such as ``credits7d`` / ``credits30d``."""
    return {
        entry["instanceId"]: Money(entry["credits"], entry["currency"])
        for entry in usage_by_instance(conn, [scope], lo, hi)
    }


def last_synced_day(conn: sqlite3.Connection, scope: str = "org") -> date | None:
    row = conn.execute(
        "SELECT MAX(day) AS d FROM credit_usage WHERE scope = ?", (scope,)
    ).fetchone()
    return date.fromisoformat(row["d"]) if row and row["d"] else None


def billing_meta(conn: sqlite3.Connection) -> tuple[str | None, str]:
    """``(billingCurrency, billingMode)`` derived from the stored org-level rows."""
    row = conn.execute(
        "SELECT MAX(currency) AS currency, SUM(credit_spend IS NOT NULL) AS with_credits,"
        " SUM(currency_spend IS NOT NULL) AS with_currency FROM credit_usage"
    ).fetchone()
    if row is None or not (row["with_credits"] or row["with_currency"]):
        return (row["currency"] if row else None), "unknown"
    mode = "credits" if (row["with_credits"] or 0) >= (row["with_currency"] or 0) else "currency"
    return row["currency"], mode


def with_percent(entries: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """Add a share-of-total percentage using credits when present, else currency."""
    unit = "credits" if any(e.get("credits") is not None for e in entries) else "currency"
    total = sum(e.get(unit) or 0.0 for e in entries)
    for e in entries:
        value = e.get(unit)
        e[key] = round(value / total * 100, 2) if total and value is not None else None
    return entries


# --- prepaid / payg ---------------------------------------------------------------------


def replace_prepaid(
    conn: sqlite3.Connection, credits: Iterable[PrepaidCredit], fetched_at: str
) -> None:
    conn.execute("DELETE FROM prepaid_credit")
    conn.executemany(
        "INSERT INTO prepaid_credit (id, credit_name, support_plan, start_date, expiration_date,"
        " total, used, remaining, remaining_percent, fetched_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                c.id,
                c.credit_name,
                c.support_plan,
                c.start_date,
                c.expiration_date,
                c.total,
                c.used,
                c.remaining,
                c.remaining_percent,
                fetched_at,
            )
            for c in credits
        ],
    )


def list_prepaid(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM prepaid_credit ORDER BY expiration_date, id").fetchall()


def upsert_payg(
    conn: sqlite3.Connection, periods: Iterable[PayAsYouGoPeriod], currency: str, fetched_at: str
) -> None:
    conn.executemany(
        "INSERT INTO payg_period (day, basic, dev_pro, enterprise, total, currency, fetched_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(day) DO UPDATE SET basic=excluded.basic, dev_pro=excluded.dev_pro,"
        " enterprise=excluded.enterprise, total=excluded.total, currency=excluded.currency,"
        " fetched_at=excluded.fetched_at",
        [
            (
                p.start_date.isoformat(),
                p.cost.basic,
                p.cost.dev_pro,
                p.cost.enterprise,
                p.total,
                currency,
                fetched_at,
            )
            for p in periods
        ],
    )


def list_payg(conn: sqlite3.Connection, lo: date, hi: date) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM payg_period WHERE day BETWEEN ? AND ? ORDER BY day",
        (lo.isoformat(), hi.isoformat()),
    ).fetchall()
