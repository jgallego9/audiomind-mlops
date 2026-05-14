# Build context must be the project root:
#   docker build -f services/worker/Dockerfile .

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY services/api-gateway/pyproject.toml ./services/api-gateway/pyproject.toml
COPY services/worker/pyproject.toml       ./services/worker/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package worker

# ---------------------------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY services/worker/app ./app

RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

CMD ["python", "-m", "app.main"]
