"""Pydantic models for the Capella Management API payloads this tool reads.

Every model allows unknown fields (``extra="allow"``) so new Capella attributes never break
the sync, and :meth:`CapellaModel.raw` returns the full payload (known + unknown keys) for the
``raw_json`` columns in the store.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

BILLING_CATEGORIES: tuple[str, ...] = (
    "operationalComputeAndStorage",
    "operationalBucketBackup",
    "operationalClusterBackup",
    "analyticsCompute",
    "analyticsStorage",
    "analyticsClusterBackup",
    "appServicesComputeAndStorage",
    "dataTransferStandard",
    "privateEndpointsStandard",
    "aiServicesLLM",
    "aiServicesAiGateway",
    "aiServicesUdsPager",
    "aiServicesSdsPager",
    "dataApiStandard",
)

ITEMIZED_CATEGORIES: tuple[str, ...] = (
    "operationalComputeAndStorage",
    "operationalBucketBackup",
    "operationalClusterBackup",
    "dataApiStandard",
    "dataTransferStandard",
    "privateEndpointsStandard",
)


class CapellaModel(BaseModel):
    """Base model: camelCase aliases, snake_case attributes, unknown fields kept."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, alias_generator=to_camel)

    def raw(self) -> dict[str, Any]:
        """Full JSON-compatible payload as Capella sent it (aliases, extras included)."""
        return self.model_dump(mode="json", by_alias=True)


# --- pagination -------------------------------------------------------------------------


class Pages(CapellaModel):
    page: int = 1
    next: int | None = None
    previous: int | None = None
    last: int = 1
    per_page: int = 0
    total_items: int = 0


class Cursor(CapellaModel):
    pages: Pages = Field(default_factory=Pages)
    hrefs: dict[str, Any] = Field(default_factory=dict)


# --- inventory --------------------------------------------------------------------------


class Organization(CapellaModel):
    id: str
    name: str
    description: str | None = None


class Project(CapellaModel):
    id: str
    name: str
    description: str | None = None


class Compute(CapellaModel):
    cpu: int
    ram: int


class Disk(CapellaModel):
    type: str | None = None
    storage: int | None = None
    iops: int | None = None


class Node(CapellaModel):
    compute: Compute
    disk: Disk | None = None


class ServiceGroup(CapellaModel):
    node: Node
    num_of_nodes: int = 0
    services: list[str] = Field(default_factory=list)


class CloudProvider(CapellaModel):
    type: str
    region: str
    cidr: str | None = None


class CouchbaseServer(CapellaModel):
    version: str | None = None


class Availability(CapellaModel):
    type: str


class Support(CapellaModel):
    plan: str
    timezone: str | None = None


class Audit(CapellaModel):
    created_at: str | None = None
    created_by: str | None = None
    modified_at: str | None = None
    modified_by: str | None = None
    version: int | None = None


class Cluster(CapellaModel):
    id: str
    name: str
    description: str | None = None
    configuration_type: str | None = None
    connection_string: str | None = None
    cloud_provider: CloudProvider
    couchbase_server: CouchbaseServer | None = None
    service_groups: list[ServiceGroup] = Field(default_factory=list)
    availability: Availability | None = None
    support: Support | None = None
    current_state: str
    app_service_id: str | None = None
    audit: Audit | None = None

    @property
    def is_free_tier(self) -> bool:
        """Free-tier clusters report ``support.plan == "free"`` and are never billed."""
        return self.support is not None and self.support.plan == "free"

    @property
    def node_count(self) -> int:
        return sum(group.num_of_nodes for group in self.service_groups)


class BucketStats(CapellaModel):
    item_count: int | None = None
    ops_per_second: int | None = None
    disk_used_in_mib: int | None = None
    memory_used_in_mib: int | None = None


class Bucket(CapellaModel):
    id: str | None = None
    name: str
    type: str | None = None
    storage_backend: str | None = None
    memory_allocation_in_mb: int | None = None
    replicas: int | None = None
    eviction_policy: str | None = None
    time_to_live_in_seconds: int | None = None
    stats: BucketStats | None = None


class AppService(CapellaModel):
    id: str
    name: str
    description: str | None = None
    cloud_provider: str | None = None
    nodes: int | None = None
    compute: Compute | None = None
    cluster_id: str
    current_state: str
    version: str | None = None
    plan: str | None = None
    audit: Audit | None = None


class AppEndpoint(CapellaModel):
    name: str
    bucket: str | None = None
    state: str | None = None


# --- billing ----------------------------------------------------------------------------


class BillingCategoryBreakdown(CapellaModel):
    category: str
    credit_spend: float | None = None
    currency_spend: float | None = None
    contribution_percent: float | None = None


class BillingPeriod(CapellaModel):
    start_date: date
    end_date: date
    categories: list[BillingCategoryBreakdown] = Field(default_factory=list)
    total_credit_spend: float | None = None
    total_currency_spend: float | None = None


class CategorizedBilling(CapellaModel):
    """The ``data`` object of ``categorizedBilling``."""

    periods: list[BillingPeriod] = Field(default_factory=list)
    total: BillingPeriod
    billing_currency: str = "USD"


class ItemizedBilling(CategorizedBilling):
    """The ``data`` object of ``itemizedBillingPerCluster``."""

    cluster_name: str
    support_plan: str


class PrepaidCredit(CapellaModel):
    id: str
    credit_name: str
    support_plan: str
    start_date: str
    expiration_date: str
    total: float
    used: float
    remaining: float
    remaining_percent: float


class PayAsYouGoCost(CapellaModel):
    basic: float = 0.0
    dev_pro: float = 0.0
    enterprise: float = 0.0


class PayAsYouGoPeriod(CapellaModel):
    start_date: date
    end_date: date
    cost: PayAsYouGoCost
    total: float = 0.0


class PayAsYouGo(CapellaModel):
    """The ``data`` object of ``payAsYouGoBilling``."""

    periods: list[PayAsYouGoPeriod] = Field(default_factory=list)
    total: PayAsYouGoPeriod
    billing_currency: str = "USD"
