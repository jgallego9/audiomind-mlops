# Build context must be the project root:
#   docker build -f services/api-gateway/Dockerfile .
# (docker-compose handles this automatically via `context: .`)

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy workspace manifests — changes here invalidate the dep-install layer,
# but source code changes do not, giving fast rebuilds.
COPY pyproject.toml uv.lock ./
COPY services/api-gateway/pyproject.toml ./services/api-gateway/pyproject.toml
COPY services/worker/pyproject.toml       ./services/worker/pyproject.toml

# Install only the api-gateway dependencies (no worker deps, no dev tools).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package api-gateway

# ---------------------------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the virtualenv produced by the builder stage.
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source.
COPY services/api-gateway/app ./app

# Run as non-root user.
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
