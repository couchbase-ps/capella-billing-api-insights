"""``insights`` command line: ``serve``, ``sync``, ``db init``."""

from __future__ import annotations

import asyncio
import json

import typer

from insights.config import load_settings
from insights.logsetup import configure_logging

app = typer.Typer(help="Capella Billing API Insights backend.", no_args_is_help=True)
db_app = typer.Typer(help="Database maintenance.", no_args_is_help=True)
app.add_typer(db_app, name="db")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind address"),
    port: int = typer.Option(8000, help="Bind port"),
) -> None:
    """Run the HTTP API with uvicorn (background sync starts with the app)."""
    import uvicorn

    from insights.api.app import create_app

    settings = load_settings()
    configure_logging(settings.log_level)
    uvicorn.run(create_app(settings), host=host, port=port, log_config=None)


@app.command()
def sync() -> None:
    """Run one sync (inventory + billing) and exit; non-zero exit on failure."""
    from insights.api.app import build_client
    from insights.store import repo
    from insights.store.db import Database
    from insights.sync.runner import SyncNotConfigured, SyncRunner, utc_now_iso

    settings = load_settings()
    configure_logging(settings.log_level)

    async def _run() -> repo.SyncRunRow:
        database = Database(settings.effective_db_path)
        database.init_schema()
        with database.session() as conn:
            repo.mark_stale_runs_failed(conn, utc_now_iso())
        client = build_client(settings)
        runner = SyncRunner(database, client, settings)
        try:
            return await runner.run()
        finally:
            if client is not None:
                await client.aclose()

    try:
        row = asyncio.run(_run())
    except SyncNotConfigured as exc:
        typer.echo(json.dumps({"status": "failed", "error": str(exc)}))
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(row.as_json(include_detail=True), indent=2))
    if row.status == "failed":
        raise typer.Exit(code=1)


@db_app.command("init")
def db_init() -> None:
    """Create the SQLite schema at DB_PATH (idempotent)."""
    from insights.store.db import Database

    settings = load_settings()
    Database(settings.effective_db_path).init_schema()
    typer.echo(f"schema ready at {settings.effective_db_path}")


if __name__ == "__main__":  # pragma: no cover
    app()
