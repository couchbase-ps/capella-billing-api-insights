"""Billing sync: per calendar-month window, org roll-up + one call per billable instance."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date

from insights.capella.client import CapellaSource
from insights.capella.models import CategorizedBilling
from insights.store import repo
from insights.store.db import Database
from insights.sync.inventory import Failure, Inventory
from insights.sync.windows import month_windows

log = logging.getLogger(__name__)


@dataclass
class BillingOutcome:
    windows: int = 0
    rows_written: int = 0
    failures: list[Failure] = field(default_factory=list)


def rows_from_billing(
    scope: str, instance_id: str, billing: CategorizedBilling
) -> list[repo.UsageRow]:
    """Flatten a categorized billing response into daily store rows.

    Windows never cross a month, so every period is one day; a multi-day period (should
    Capella ever return one) is stored under its start date.
    """
    rows: list[repo.UsageRow] = []
    for period in billing.periods:
        for entry in period.categories:
            if entry.credit_spend is None and entry.currency_spend is None:
                continue
            rows.append(
                repo.UsageRow(
                    day=period.start_date,
                    scope=scope,
                    instance_id=instance_id,
                    category=entry.category,
                    credit_spend=entry.credit_spend,
                    currency_spend=entry.currency_spend,
                    currency=billing.billing_currency,
                )
            )
    return rows


def _store_rows(
    db: Database,
    scope: str,
    instance_id: str,
    lo: date,
    hi: date,
    rows: list[repo.UsageRow],
    now: str,
) -> int:
    with db.session() as conn:
        return repo.replace_credit_usage(conn, scope, instance_id, lo, hi, rows, now)


async def _sync_instance(
    client: CapellaSource,
    db: Database,
    scope: str,
    instance_id: str,
    lo: date,
    hi: date,
    now: str,
    outcome: BillingOutcome,
) -> None:
    try:
        billing = await client.categorized_billing(
            lo, hi, instance_ids=[instance_id] if instance_id else None
        )
        rows = rows_from_billing(scope, instance_id, billing)
        outcome.rows_written += await asyncio.to_thread(
            _store_rows, db, scope, instance_id, lo, hi, rows, now
        )
    except Exception as exc:
        log.warning("billing %s/%s %s..%s failed: %s", scope, instance_id or "-", lo, hi, exc)
        outcome.failures.append(Failure(scope, instance_id, f"{lo}..{hi}: {exc}"))


async def sync_billing(
    client: CapellaSource,
    db: Database,
    inventory: Inventory,
    start: date,
    end: date,
    now: str,
) -> BillingOutcome:
    """Fetch and store credit usage for ``[start, end]`` plus PAYG periods and prepaid credits."""
    outcome = BillingOutcome()
    for lo, hi in month_windows(start, end):
        outcome.windows += 1
        await _sync_instance(client, db, "org", "", lo, hi, now, outcome)
        for _, cluster in inventory.billable_clusters:
            await _sync_instance(client, db, "cluster", cluster.id, lo, hi, now, outcome)
        for service in inventory.app_services:
            await _sync_instance(client, db, "appservice", service.id, lo, hi, now, outcome)
        for _, analytics in inventory.analytics:
            await _sync_instance(client, db, "analytics", analytics.id, lo, hi, now, outcome)
        try:
            payg = await client.pay_as_you_go(lo, hi)
            await asyncio.to_thread(_store_payg, db, payg.periods, payg.billing_currency, now)
        except Exception as exc:
            log.warning("payg %s..%s failed: %s", lo, hi, exc)
            outcome.failures.append(Failure("org", "", f"payAsYouGo {lo}..{hi}: {exc}"))

    try:
        credits = await client.prepaid_credits()
        await asyncio.to_thread(_store_prepaid, db, credits, now)
    except Exception as exc:
        log.warning("prepaid credits failed: %s", exc)
        outcome.failures.append(Failure("org", "", f"prepaidCredits: {exc}"))
    return outcome


def _store_payg(db: Database, periods: list, currency: str, now: str) -> None:
    with db.session() as conn:
        repo.upsert_payg(conn, periods, currency, now)


def _store_prepaid(db: Database, credits: list, now: str) -> None:
    with db.session() as conn:
        repo.replace_prepaid(conn, credits, now)
