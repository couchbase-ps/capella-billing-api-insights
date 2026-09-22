"""Fixture-backed ``CapellaSource`` for demos (``CAPELLA_MOCK=true``) and tests.

Inventory comes from ``fixtures/inventory.json``; billing is synthesised deterministically by
:mod:`insights.capella.synth`. The mock never sleeps and never touches the network.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from insights.capella import synth
from insights.capella.models import (
    ITEMIZED_CATEGORIES,
    AnalyticsCluster,
    AppEndpoint,
    AppService,
    Bucket,
    CategorizedBilling,
    Cluster,
    ItemizedBilling,
    Organization,
    PayAsYouGo,
    PrepaidCredit,
    Project,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_PLAN_TITLES = {"basic": "Basic", "developer pro": "DeveloperPro", "enterprise": "Enterprise"}


class MockCapellaClient:
    """Implements :class:`insights.capella.client.CapellaSource` from JSON fixtures."""

    def __init__(
        self,
        fixtures_dir: Path | None = None,
        *,
        today: date | None = None,
        org_id: str | None = None,
    ) -> None:
        root = fixtures_dir or FIXTURES_DIR
        self._inventory: dict[str, Any] = json.loads((root / "inventory.json").read_text())
        self._prepaid: dict[str, Any] = json.loads((root / "prepaid.json").read_text())
        self._today = today or datetime.now(UTC).date()
        self.requests_made = 0
        self.org_id = org_id or self._inventory["organizations"][0]["id"]

    async def aclose(self) -> None:
        return None

    def _hit(self) -> None:
        self.requests_made += 1

    # --- inventory ----------------------------------------------------------------------

    async def list_organizations(self) -> list[Organization]:
        self._hit()
        return [Organization.model_validate(o) for o in self._inventory["organizations"]]

    async def list_projects(self) -> list[Project]:
        self._hit()
        return [Project.model_validate(p) for p in self._inventory["projects"]]

    async def list_clusters(self, project_id: str) -> list[Cluster]:
        self._hit()
        rows = self._inventory["clusters"].get(project_id, [])
        return [Cluster.model_validate(c) for c in rows]

    async def list_buckets(self, project_id: str, cluster_id: str) -> list[Bucket]:
        self._hit()
        rows = self._inventory["buckets"].get(cluster_id, [])
        return [Bucket.model_validate(b) for b in rows]

    async def list_app_services(self) -> list[AppService]:
        self._hit()
        return [AppService.model_validate(a) for a in self._inventory["appServices"]]

    async def list_app_endpoints(
        self, project_id: str, cluster_id: str, app_service_id: str
    ) -> list[AppEndpoint]:
        self._hit()
        rows = self._inventory["appEndpoints"].get(app_service_id, [])
        return [AppEndpoint.model_validate(e) for e in rows]

    async def list_analytics_clusters(self, project_id: str) -> list[AnalyticsCluster]:
        self._hit()
        rows = self._inventory.get("analyticsClusters", {}).get(project_id, [])
        return [AnalyticsCluster.model_validate(a) for a in rows]

    # --- profiles -----------------------------------------------------------------------

    def _profiles(self) -> list[synth.InstanceProfile]:
        profiles: list[synth.InstanceProfile] = []
        cluster_project: dict[str, str] = {}
        for project_id, clusters in self._inventory["clusters"].items():
            for raw in clusters:
                cluster = Cluster.model_validate(raw)
                cluster_project[cluster.id] = project_id
                profiles.append(synth.cluster_profile(cluster, project_id))
        for raw in self._inventory["appServices"]:
            service = AppService.model_validate(raw)
            profiles.append(
                synth.app_service_profile(service, cluster_project.get(service.cluster_id))
            )
        for project_id, rows in self._inventory.get("analyticsClusters", {}).items():
            for raw in rows:
                profiles.append(
                    synth.analytics_profile(AnalyticsCluster.model_validate(raw), project_id)
                )
        return profiles

    def _select(
        self, instance_ids: Sequence[str] | None, project_ids: Sequence[str] | None
    ) -> list[synth.InstanceProfile]:
        profiles = self._profiles()
        if instance_ids:
            wanted = set(instance_ids)
            return [p for p in profiles if p.instance_id in wanted]
        if project_ids:
            wanted = set(project_ids)
            return [p for p in profiles if p.project_id in wanted]
        return [*profiles, synth.org_extras_profile(self.org_id or "org")]

    # --- billing ------------------------------------------------------------------------

    async def categorized_billing(
        self,
        start: date,
        end: date,
        instance_ids: Sequence[str] | None = None,
        project_ids: Sequence[str] | None = None,
        categories: Sequence[str] | None = None,
    ) -> CategorizedBilling:
        self._hit()
        wanted = set(categories) if categories else None
        periods, total = synth.billing_periods(
            self._select(instance_ids, project_ids), start, end, wanted
        )
        return CategorizedBilling(periods=periods, total=total, billing_currency="USD")

    async def itemized_billing(
        self, project_id: str, cluster_id: str, start: date, end: date
    ) -> ItemizedBilling:
        self._hit()
        raw = next(
            (c for c in self._inventory["clusters"].get(project_id, []) if c["id"] == cluster_id),
            None,
        )
        if raw is None:
            raise KeyError(cluster_id)
        cluster = Cluster.model_validate(raw)
        periods, total = synth.billing_periods(
            [synth.cluster_profile(cluster, project_id)], start, end, set(ITEMIZED_CATEGORIES)
        )
        plan = cluster.support.plan if cluster.support else "basic"
        return ItemizedBilling(
            cluster_name=cluster.name,
            support_plan=_PLAN_TITLES.get(plan, plan),
            periods=periods,
            total=total,
            billing_currency="USD",
        )

    async def prepaid_credits(self) -> list[PrepaidCredit]:
        self._hit()
        credits: list[PrepaidCredit] = []
        for raw in self._prepaid["credits"]:
            start = self._today + timedelta(days=int(raw.get("startOffsetDays", 0)))
            expires = self._today + timedelta(days=int(raw.get("expiresInDays", 365)))
            total = float(raw["total"])
            used = float(raw["used"])
            remaining = round(total - used, 2)
            credits.append(
                PrepaidCredit(
                    id=raw["id"],
                    credit_name=raw["creditName"],
                    support_plan=raw["supportPlan"],
                    start_date=f"{start.isoformat()}T00:00:00Z",
                    expiration_date=f"{expires.isoformat()}T23:59:59Z",
                    total=total,
                    used=used,
                    remaining=remaining,
                    remaining_percent=round(remaining / total * 100, 2) if total else 0.0,
                )
            )
        return credits

    async def pay_as_you_go(self, start: date, end: date) -> PayAsYouGo:
        self._hit()
        periods, total = synth.payg_periods(self.org_id or "org", start, end)
        return PayAsYouGo(periods=periods, total=total, billing_currency="USD")
