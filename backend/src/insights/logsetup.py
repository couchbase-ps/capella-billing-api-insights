"""JSON logging to stdout. The API key is never logged (only method + path are)."""

from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str = "info") -> None:
    """Install a JSON formatter on the root logger at ``level``."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s", rename_fields={"asctime": "ts"}
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    logging.getLogger("httpx").setLevel(logging.WARNING)
