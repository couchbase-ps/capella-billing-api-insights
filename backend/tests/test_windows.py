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


def test_mock_mode_uses_its_own_database_file() -> None:
    from insights.config import Settings

    assert Settings(capella_mock=False, db_path="/data/insights.db").effective_db_path == (
        "/data/insights.db"
    )
    assert Settings(capella_mock=True, db_path="/data/insights.db").effective_db_path == (
        "/data/insights-mock.db"
    )
    assert Settings(capella_mock=True, db_path="/data/insights").effective_db_path == (
        "/data/insights-mock"
    )


def test_split_rows_shares_project_analytics_spend_by_size() -> None:
    from datetime import date as _date

    from insights.store import repo
    from insights.sync.billing import split_rows

    rows = [
        repo.UsageRow(
            day=_date(2026, 8, 1),
            scope="analytics",
            instance_id="",
            category="analyticsCompute",
            credit_spend=100.0,
            currency_spend=None,
            currency="USD",
        )
    ]
    parts = split_rows(rows, {"big": 3.0, "small": 1.0})
    assert parts["big"][0].credit_spend == 75.0
    assert parts["small"][0].credit_spend == 25.0
    assert parts["big"][0].instance_id == "big"
    single = split_rows(rows, {"only": 8.0})
    assert single["only"][0].credit_spend == 100.0
