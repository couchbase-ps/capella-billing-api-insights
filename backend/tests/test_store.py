"""Store semantics: idempotent schema, upserts, window replacement, aggregations."""

from __future__ import annotations

from datetime import date

from insights.capella.models import Organization, Project
from insights.store import repo
from insights.store.db import Database


def row(
    day: date, category: str, credits: float | None, scope: str = "cluster", inst: str = "c1"
) -> repo.UsageRow:
    return repo.UsageRow(day, scope, inst, category, credits, None, "USD")


def test_init_schema_is_idempotent(db: Database) -> None:
    db.init_schema()
    db.init_schema()
    with db.session() as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"organization", "cluster", "credit_usage", "analytics_cluster", "sync_run"} <= tables
    with db.session() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_replace_window_leaves_other_windows_untouched(db: Database) -> None:
    with db.session() as conn:
        repo.replace_credit_usage(
            conn,
            "cluster",
            "c1",
            date(2026, 7, 1),
            date(2026, 7, 31),
            [row(date(2026, 7, 10), "operationalComputeAndStorage", 10.0)],
            "t1",
        )
        repo.replace_credit_usage(
            conn,
            "cluster",
            "c1",
            date(2026, 8, 1),
            date(2026, 8, 31),
            [
                row(date(2026, 8, 1), "operationalComputeAndStorage", 5.0),
                row(date(2026, 8, 2), "dataTransferStandard", 1.0),
            ],
            "t1",
        )
    # re-sync August with corrected figures: day 2 disappears, day 1 changes; July untouched
    with db.session() as conn:
        repo.replace_credit_usage(
            conn,
            "cluster",
            "c1",
            date(2026, 8, 1),
            date(2026, 8, 31),
            [row(date(2026, 8, 1), "operationalComputeAndStorage", 7.5)],
            "t2",
        )
        rows = repo.query_usage(conn, "cluster", "c1", date(2026, 7, 1), date(2026, 8, 31))
    assert [(r.day.isoformat(), r.credit_spend) for r in rows] == [
        ("2026-07-10", 10.0),
        ("2026-08-01", 7.5),
    ]


def test_replace_window_is_scoped_to_instance(db: Database) -> None:
    with db.session() as conn:
        repo.replace_credit_usage(
            conn,
            "cluster",
            "c1",
            date(2026, 8, 1),
            date(2026, 8, 31),
            [row(date(2026, 8, 1), "x", 1.0)],
            "t",
        )
        repo.replace_credit_usage(
            conn,
            "cluster",
            "c2",
            date(2026, 8, 1),
            date(2026, 8, 31),
            [row(date(2026, 8, 1), "x", 2.0, inst="c2")],
            "t",
        )
        repo.replace_credit_usage(
            conn,
            "org",
            "",
            date(2026, 8, 1),
            date(2026, 8, 31),
            [row(date(2026, 8, 1), "x", 9.0, scope="org", inst="")],
            "t",
        )
        repo.replace_credit_usage(
            conn, "cluster", "c1", date(2026, 8, 1), date(2026, 8, 31), [], "t"
        )
        assert repo.query_usage(conn, "cluster", "c1", date(2026, 8, 1), date(2026, 8, 31)) == []
        assert (
            len(repo.query_usage(conn, "cluster", "c2", date(2026, 8, 1), date(2026, 8, 31))) == 1
        )
        assert repo.usage_total(conn, "org", "", date(2026, 8, 1), date(2026, 8, 31)).credits == 9.0


def test_null_credits_stay_null(db: Database) -> None:
    with db.session() as conn:
        repo.replace_credit_usage(
            conn,
            "cluster",
            "c1",
            date(2026, 8, 1),
            date(2026, 8, 31),
            [repo.UsageRow(date(2026, 8, 1), "cluster", "c1", "x", None, 12.5, "EUR")],
            "t",
        )
        total = repo.usage_total(conn, "cluster", "c1", date(2026, 8, 1), date(2026, 8, 31))
        assert total.credits is None and total.currency == 12.5
        assert repo.billing_meta(conn) == ("EUR", "currency")
        empty = repo.usage_total(conn, "cluster", "nope", date(2026, 8, 1), date(2026, 8, 31))
        assert empty.credits is None and empty.currency is None


def test_aggregations(db: Database) -> None:
    with db.session() as conn:
        repo.replace_credit_usage(
            conn,
            "cluster",
            "c1",
            date(2026, 7, 1),
            date(2026, 8, 31),
            [
                row(date(2026, 7, 31), "a", 1.0),
                row(date(2026, 8, 1), "a", 2.0),
                row(date(2026, 8, 1), "b", 1.0),
                row(date(2026, 8, 2), "a", 4.0),
            ],
            "t",
        )
        months = repo.usage_by_period(
            conn, "cluster", "c1", date(2026, 7, 1), date(2026, 8, 31), "month"
        )
        assert [(m["period"], m["category"], m["credits"]) for m in months] == [
            ("2026-07", "a", 1.0),
            ("2026-08", "a", 6.0),
            ("2026-08", "b", 1.0),
        ]
        cats = repo.usage_by_category(conn, "cluster", "c1", date(2026, 8, 1), date(2026, 8, 31))
        assert cats[0] == {
            "category": "a",
            "credits": 6.0,
            "currency": None,
            "contributionPercent": 85.71,
        }
        per_instance = repo.credits_per_instance(
            conn, "cluster", date(2026, 8, 1), date(2026, 8, 31)
        )
        assert per_instance["c1"].credits == 7.0
        assert repo.last_synced_day(conn, "cluster") == date(2026, 8, 2)
        assert repo.last_synced_day(conn, "org") is None


def test_inventory_upsert_and_prune(db: Database) -> None:
    org = Organization(id="o1", name="Acme")
    with db.session() as conn:
        repo.upsert_organization(conn, org, "t1")
        repo.upsert_projects(
            conn, "o1", [Project(id="p1", name="One"), Project(id="p2", name="Two")]
        )
        repo.upsert_projects(conn, "o1", [Project(id="p1", name="One renamed")])
        repo.prune_projects(conn, ["p1"])
        projects = repo.list_projects_with_counts(conn)
    assert projects == [{"id": "p1", "name": "One renamed", "clusterCount": 0}]
    with db.session() as conn:
        assert repo.get_organization(conn)["name"] == "Acme"


def test_sync_run_lifecycle(db: Database) -> None:
    with db.session() as conn:
        run_id = repo.create_sync_run(conn, "2026-09-22T00:00:00Z")
        repo.finish_sync_run(
            conn,
            run_id,
            finished_at="2026-09-22T00:01:00Z",
            status="partial",
            requests_made=12,
            error=None,
            detail={
                **repo.empty_detail(),
                "failures": [{"scope": "cluster", "instanceId": "c", "message": "m"}],
            },
        )
        runs = repo.list_sync_runs(conn)
    assert runs[0].status == "partial"
    assert runs[0].as_json(include_detail=True)["detail"]["failures"][0]["instanceId"] == "c"
    assert "detail" not in runs[0].as_json()
