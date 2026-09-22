"""Report definitions and the registry the API serves them from.

Adding a report means registering one more :class:`ReportDefinition`; the HTTP layer stays
untouched (design spec §3.6 / §8).
"""

from __future__ import annotations

import csv
import io
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

ColumnType = Literal["string", "number", "date", "credits", "currency"]
ParamType = Literal["date", "string", "number"]


class ReportError(Exception):
    """Invalid report parameters (surfaced as HTTP 400)."""


@dataclass(frozen=True)
class ReportParam:
    name: str
    type: ParamType
    required: bool = False
    description: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "description": self.description,
        }


@dataclass(frozen=True)
class ReportColumn:
    key: str
    label: str
    type: ColumnType

    def as_json(self) -> dict[str, str]:
        return {"key": self.key, "label": self.label, "type": self.type}


@dataclass
class ReportContext:
    """What a report receives: an open store connection, the range and extra params."""

    conn: sqlite3.Connection
    date_from: date
    date_to: date
    params: dict[str, str] = field(default_factory=dict)

    def require(self, name: str) -> str:
        value = self.params.get(name)
        if not value:
            raise ReportError(f"missing required parameter '{name}'")
        return value


@dataclass
class ReportResult:
    columns: list[ReportColumn]
    rows: list[dict[str, Any]]
    totals: dict[str, Any] | None = None


ReportRunner = Callable[[ReportContext], ReportResult]


@dataclass(frozen=True)
class ReportDefinition:
    key: str
    title: str
    description: str
    params: tuple[ReportParam, ...]
    run: ReportRunner

    def describe(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "description": self.description,
            "params": [p.as_json() for p in self.params],
        }


class ReportRegistry:
    """Ordered registry of report definitions keyed by ``key``."""

    def __init__(self) -> None:
        self._defs: dict[str, ReportDefinition] = {}

    def register(self, definition: ReportDefinition) -> ReportDefinition:
        self._defs[definition.key] = definition
        return definition

    def get(self, key: str) -> ReportDefinition | None:
        return self._defs.get(key)

    def list(self) -> list[ReportDefinition]:
        return list(self._defs.values())


registry = ReportRegistry()
"""Process-wide registry; the only intentional piece of global mutable state."""


def result_to_json(
    definition: ReportDefinition, ctx: ReportContext, result: ReportResult
) -> dict[str, Any]:
    return {
        "key": definition.key,
        "title": definition.title,
        "from": ctx.date_from.isoformat(),
        "to": ctx.date_to.isoformat(),
        "columns": [c.as_json() for c in result.columns],
        "rows": result.rows,
        "totals": result.totals,
    }


def result_to_csv(result: ReportResult) -> str:
    """Serialise rows (and a trailing totals row when present) as CSV text."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([c.label for c in result.columns])
    for row in result.rows:
        writer.writerow([_cell(row.get(c.key)) for c in result.columns])
    if result.totals:
        writer.writerow(
            [
                "TOTAL" if i == 0 else _cell(result.totals.get(c.key))
                for i, c in enumerate(result.columns)
            ]
        )
    return buffer.getvalue()


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)
