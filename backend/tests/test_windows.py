from datetime import date

import pytest

from insights.sync.windows import month_end, month_windows, sync_range


def test_month_end() -> None:
    assert month_end(date(2024, 2, 10)) == date(2024, 2, 29)
    assert month_end(date(2026, 12, 1)) == date(2026, 12, 31)


def test_single_month_window_is_clipped() -> None:
    assert month_windows(date(2026, 8, 5), date(2026, 8, 20)) == [
        (date(2026, 8, 5), date(2026, 8, 20))
    ]


def test_windows_never_cross_month_boundary() -> None:
    windows = month_windows(date(2026, 6, 20), date(2026, 9, 3))
    assert windows == [
        (date(2026, 6, 20), date(2026, 6, 30)),
        (date(2026, 7, 1), date(2026, 7, 31)),
        (date(2026, 8, 1), date(2026, 8, 31)),
        (date(2026, 9, 1), date(2026, 9, 3)),
    ]
    for lo, hi in windows:
        assert (lo.year, lo.month) == (hi.year, hi.month)


def test_windows_across_year_boundary() -> None:
    assert month_windows(date(2025, 12, 31), date(2026, 1, 1)) == [
        (date(2025, 12, 31), date(2025, 12, 31)),
        (date(2026, 1, 1), date(2026, 1, 1)),
    ]


def test_single_day_window() -> None:
    assert month_windows(date(2026, 3, 3), date(2026, 3, 3)) == [
        (date(2026, 3, 3), date(2026, 3, 3))
    ]


def test_empty_range_yields_no_windows() -> None:
    assert month_windows(date(2026, 3, 4), date(2026, 3, 3)) == []


@pytest.mark.parametrize(
    ("last", "expected_start"),
    [
        (None, date(2026, 6, 24)),  # first sync: full backfill
        (date(2026, 9, 21), date(2026, 9, 15)),  # up to date: only the refresh window
        (date(2026, 9, 1), date(2026, 9, 2)),  # gap larger than refresh: from first missing day
        (date(2026, 1, 1), date(2026, 6, 24)),  # very old: bounded by backfill horizon
    ],
)
def test_sync_range(last: date | None, expected_start: date) -> None:
    today = date(2026, 9, 22)
    assert sync_range(today, last, 90, 7) == (expected_start, date(2026, 9, 21))


def test_sync_range_end_is_yesterday() -> None:
    start, end = sync_range(date(2026, 3, 1), None, 10, 3) or (None, None)
    assert end == date(2026, 2, 28)
    assert start == date(2026, 2, 19)


def test_sync_range_nothing_to_do() -> None:
    assert sync_range(date(2026, 9, 22), date(2026, 9, 21), 0, 0) is None
