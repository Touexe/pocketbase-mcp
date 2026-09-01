# syntax=docker/dockerfile:1

# ---- builder: resolve deps into a self-contained venv ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# git needed: pypocketbase is a git source in pyproject.toml
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer 1: deps only (cached unless lock/manifest change)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Layer 2: project source
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime: copy venv + source, no build tooling ----
FROM python:3.12-slim-bookworm AS runtime

RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    POCKETBASE_MCP_HOST=0.0.0.0 \
    POCKETBASE_MCP_PORT=8000

USER app
EXPOSE 8000

ENTRYPOINT ["pocketbase-mcp"]
CMD ["--http"]
