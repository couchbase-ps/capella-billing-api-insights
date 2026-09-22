"""Pure date-window arithmetic for the billing sync."""

from __future__ import annotations

import calendar
from datetime import date, timedelta


def month_end(day: date) -> date:
    """Last day of the calendar month containing ``day``."""
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def month_windows(start: date, end: date) -> list[tuple[date, date]]:
    """Split ``[start, end]`` into windows that never cross a calendar-month boundary.

    Capella returns daily periods only for ranges inside one month, so every window is
    ``[max(start, first-of-month), min(end, last-of-month)]``. An empty range (``end < start``)
    yields no windows.
    """
    if end < start:
        return []
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        last = min(month_end(cursor), end)
        windows.append((cursor, last))
        cursor = last + timedelta(days=1)
    return windows


def sync_range(
    today: date,
    last_synced_day: date | None,
    backfill_days: int,
    refresh_days: int,
) -> tuple[date, date] | None:
    """Compute the ``[start, yesterday]`` range a sync must fetch.

    ``start`` is the earlier of the first day not yet stored (bounded by the backfill
    horizon) and the trailing refresh window that catches Capella's late corrections.
    Returns ``None`` when there is nothing to fetch (for example the very first day of an
    installation with ``backfill_days=0``).
    """
    end = today - timedelta(days=1)
    horizon = today - timedelta(days=max(backfill_days, 0))
    if last_synced_day is None:
        missing_from = horizon
    else:
        missing_from = max(last_synced_day + timedelta(days=1), horizon)
    refresh_from = today - timedelta(days=max(refresh_days, 0))
    start = min(missing_from, refresh_from)
    if start > end:
        return None
    return start, end
