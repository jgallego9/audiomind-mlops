from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    uptime_seconds: float


class CheckResult(BaseModel):
    status: Literal["ok", "degraded", "unavailable", "error"]
    latency_ms: float | None = None
    message: str | None = None


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, CheckResult]
