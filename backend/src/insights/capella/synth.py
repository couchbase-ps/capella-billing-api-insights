"""Deterministic synthetic billing for the mock client.

Amounts depend only on the instance id, its size profile and the calendar day, so any date
range yields stable figures and re-syncing a window reproduces the same rows.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from datetime import date, timedelta

from insights.capella.models import (
    AnalyticsCluster,
    AppService,
    BillingCategoryBreakdown,
    BillingPeriod,
    Cluster,
    PayAsYouGoCost,
    PayAsYouGoPeriod,
)
from insights.sync.windows import month_windows

COMPUTE = "operationalComputeAndStorage"
BUCKET_BACKUP = "operationalBucketBackup"
TRANSFER = "dataTransferStandard"
APP_SERVICES = "appServicesComputeAndStorage"
PRIVATE_ENDPOINTS = "privateEndpointsStandard"
ANALYTICS_COMPUTE = "analyticsCompute"
ANALYTICS_STORAGE = "analyticsStorage"
ANALYTICS_BACKUP = "analyticsClusterBackup"


def noise(key: str, day: date, salt: str = "") -> float:
    """Stable multiplicative jitter in ``[0.9, 1.1)`` for a key/day pair."""
    digest = zlib.crc32(f"{key}|{day.isoformat()}|{salt}".encode())
    return 0.9 + (digest % 2000) / 10000.0


@dataclass
class InstanceProfile:
    """What an instance costs per day, before jitter."""

    instance_id: str
    project_id: str | None
    scope: str
    daily: dict[str, float] = field(default_factory=dict)

    def amounts(self, day: date) -> dict[str, float]:
        """Per-category credits for one day (rounded, jittered, zero-free)."""
        out: dict[str, float] = {}
        for category, base in self.daily.items():
            value = round(base * noise(self.instance_id, day, category), 4)
            if value > 0:
                out[category] = value
        return out


def cluster_profile(cluster: Cluster, project_id: str | None) -> InstanceProfile:
    """Operational cluster: compute proportional to nodes x cpu, backups and transfer on top."""
    if cluster.is_free_tier:
        return InstanceProfile(cluster.id, project_id, "cluster", {})
    if cluster.current_state in {"turnedOff", "turningOff", "offline"}:
        storage = sum(
            group.num_of_nodes * ((group.node.disk.storage if group.node.disk else 0) or 0)
            for group in cluster.service_groups
        )
        return InstanceProfile(cluster.id, project_id, "cluster", {COMPUTE: storage * 0.002})
    compute = sum(
        group.num_of_nodes * (group.node.compute.cpu * 0.6 + group.node.compute.ram * 0.05)
        for group in cluster.service_groups
    )
    return InstanceProfile(
        cluster.id,
        project_id,
        "cluster",
        {COMPUTE: compute, BUCKET_BACKUP: compute * 0.06, TRANSFER: compute * 0.03},
    )


def app_service_profile(service: AppService, project_id: str | None) -> InstanceProfile:
    nodes = service.nodes or 0
    cpu = service.compute.cpu if service.compute else 0
    ram = service.compute.ram if service.compute else 0
    return InstanceProfile(
        service.id, project_id, "appservice", {APP_SERVICES: nodes * (cpu * 0.5 + ram * 0.05)}
    )


def analytics_profile(cluster: AnalyticsCluster, project_id: str | None) -> InstanceProfile:
    """Analytics cluster: compute dominant, storage and backup smaller."""
    if cluster.current_state in {"turnedOff", "turningOff", "offline"}:
        return InstanceProfile(cluster.id, project_id, "analytics", {ANALYTICS_STORAGE: 1.2})
    compute = cluster.nodes * (cluster.compute.cpu * 0.7 + cluster.compute.ram * 0.04)
    return InstanceProfile(
        cluster.id,
        project_id,
        "analytics",
        {
            ANALYTICS_COMPUTE: compute,
            ANALYTICS_STORAGE: compute * 0.12,
            ANALYTICS_BACKUP: compute * 0.04,
        },
    )


def org_extras_profile(org_id: str) -> InstanceProfile:
    """Spend that belongs to no instance (shows up as "unattributed")."""
    return InstanceProfile(org_id, None, "org", {PRIVATE_ENDPOINTS: 0.5})


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _sum_amounts(
    profiles: list[InstanceProfile], days: list[date], categories: set[str] | None
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for profile in profiles:
        for day in days:
            for category, value in profile.amounts(day).items():
                if categories and category not in categories:
                    continue
                totals[category] = totals.get(category, 0.0) + value
    return {k: round(v, 4) for k, v in totals.items()}


def _period(start: date, end: date, totals: dict[str, float]) -> BillingPeriod:
    grand = round(sum(totals.values()), 4)
    breakdown = [
        BillingCategoryBreakdown(
            category=category,
            credit_spend=value,
            currency_spend=None,
            contribution_percent=round(value / grand * 100, 2) if grand else 0.0,
        )
        for category, value in sorted(totals.items())
    ]
    return BillingPeriod(
        start_date=start,
        end_date=end,
        categories=breakdown,
        total_credit_spend=grand if breakdown else None,
        total_currency_spend=None,
    )


def billing_periods(
    profiles: list[InstanceProfile],
    start: date,
    end: date,
    categories: set[str] | None = None,
) -> tuple[list[BillingPeriod], BillingPeriod]:
    """Periods per Capella's month-window rule plus the aggregate ``total`` period.

    Inside one calendar month each period is a day; across months each period is a month.
    """
    same_month = (start.year, start.month) == (end.year, end.month)
    if same_month:
        spans = [(day, day) for day in _days(start, end)]
    else:
        spans = month_windows(start, end)
    periods = [
        _period(lo, hi, _sum_amounts(profiles, _days(lo, hi), categories)) for lo, hi in spans
    ]
    periods = [p for p in periods if p.categories]
    total = _period(start, end, _sum_amounts(profiles, _days(start, end), categories))
    return periods, total


def payg_periods(
    org_id: str, start: date, end: date
) -> tuple[list[PayAsYouGoPeriod], PayAsYouGoPeriod]:
    """Small monthly pay-as-you-go amounts, deterministic per month."""
    periods: list[PayAsYouGoPeriod] = []
    for lo, hi in month_windows(start, end):
        days = (hi - lo).days + 1
        scale = days / 30.0
        cost = PayAsYouGoCost(
            basic=0.0,
            dev_pro=round(12.5 * scale * noise(org_id, lo, "devPro"), 2),
            enterprise=round(30.0 * scale * noise(org_id, lo, "enterprise"), 2),
        )
        total = round(cost.basic + cost.dev_pro + cost.enterprise, 2)
        periods.append(PayAsYouGoPeriod(start_date=lo, end_date=hi, cost=cost, total=total))
    agg = PayAsYouGoCost(
        basic=round(sum(p.cost.basic for p in periods), 2),
        dev_pro=round(sum(p.cost.dev_pro for p in periods), 2),
        enterprise=round(sum(p.cost.enterprise for p in periods), 2),
    )
    total = PayAsYouGoPeriod(
        start_date=start,
        end_date=end,
        cost=agg,
        total=round(agg.basic + agg.dev_pro + agg.enterprise, 2),
    )
    return periods, total
