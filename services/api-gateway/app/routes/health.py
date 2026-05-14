import time

from fastapi import APIRouter

from app.models.health import CheckResult, HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])

_START_TIME = time.monotonic()


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    """Return 200 as long as the process is running."""
    return HealthResponse(status="ok", uptime_seconds=time.monotonic() - _START_TIME)


@router.get("/ready", response_model=ReadyResponse, summary="Readiness probe")
async def ready() -> ReadyResponse:
    """Check downstream dependencies and return readiness status.

    Each dependency check is added here in subsequent tasks (Redis, Qdrant…).
    Returns 200 even when degraded so Kubernetes keeps routing traffic;
    the ``status`` field signals the actual health to consumers.
    """
    checks: dict[str, CheckResult] = {}
    # TODO(F1-5): add Redis check
    # TODO(F1-6): add Qdrant check
    all_ok = all(c.status == "ok" for c in checks.values()) if checks else True
    return ReadyResponse(
        status="ready" if all_ok else "not_ready",
        checks=checks,
    )
