# Capella Billing API Insights - backend image (Python 3.12 + uv)
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.7.20 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first (cached unless pyproject/lock change).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the package itself.
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    DB_PATH=/data/insights.db

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000

CMD ["insights", "serve"]
