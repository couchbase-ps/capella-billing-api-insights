"""Display labels and fixed ordering for billing categories and support plans.

Mirrors the columns of Capella's own usage report (docs/custom-reports.md).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

APP_SERVICES_VARIABLE = "appServicesVariable"
"""Synthetic category: no API code yet, column kept for parity with the Capella usage report."""

CATEGORY_LABELS: tuple[tuple[str, str], ...] = (
    ("operationalBucketBackup", "Backup"),
    ("operationalClusterBackup", "Cluster Backup"),
    ("operationalComputeAndStorage", "Cluster"),
    ("dataTransferStandard", "Data Transfer"),
    ("privateEndpointsStandard", "Private Endpoints"),
    ("dataApiStandard", "Data API"),
    ("analyticsCompute", "Columnar Compute"),
    ("analyticsStorage", "Columnar Storage"),
    ("analyticsClusterBackup", "Columnar Backup"),
    ("appServicesComputeAndStorage", "AppServices Fixed"),
    (APP_SERVICES_VARIABLE, "AppServices Variable"),
    ("aiServicesLLM", "AI LLM"),
    ("aiServicesAiGateway", "AI Gateway"),
    ("aiServicesUdsPager", "AI UDS Pager"),
    ("aiServicesSdsPager", "AI SDS Pager"),
)

_LABEL_BY_CODE = dict(CATEGORY_LABELS)

PLAN_ORDER: tuple[str, ...] = ("Basic", "Developer Pro", "Enterprise")
UNATTRIBUTED = "Unattributed"

_PLAN_ALIASES = {
    "basic": "Basic",
    "developer pro": "Developer Pro",
    "developerpro": "Developer Pro",
    "devpro": "Developer Pro",
    "enterprise": "Enterprise",
}


def humanise(code: str) -> str:
    """``aiServicesFooBar`` -> ``Ai Services Foo Bar`` for categories we do not know yet."""
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", code).replace("_", " ").split()
    return " ".join(w[:1].upper() + w[1:] for w in words) or code


def category_label(code: str) -> str:
    return _LABEL_BY_CODE.get(code) or humanise(code)


def category_order(seen: Iterable[str]) -> list[tuple[str, str]]:
    """Fixed ``(code, label)`` order plus any unknown API category appended (sorted)."""
    known = {code for code, _ in CATEGORY_LABELS}
    extra = sorted({c for c in seen if c not in known})
    return [*CATEGORY_LABELS, *((c, humanise(c)) for c in extra)]


def normalise_plan(plan: str | None) -> str | None:
    """Capella plan codes (``developer pro``) -> report labels (``Developer Pro``)."""
    if not plan:
        return None
    key = plan.strip().lower().removeprefix("plan:").strip()
    return _PLAN_ALIASES.get(key) or humanise(plan.strip())


def plan_sort_key(plan: str) -> tuple[int, str]:
    """Basic, Developer Pro, Enterprise, other plans alphabetically, Unattributed last."""
    if plan == UNATTRIBUTED:
        return (2, "")
    if plan in PLAN_ORDER:
        return (0, str(PLAN_ORDER.index(plan)))
    return (1, plan)
