from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler  # type: ignore[import-untyped]
from slowapi.errors import RateLimitExceeded  # type: ignore[import-untyped]

from app.config import get_settings
from app.middleware.rate_limit import limiter
from app.middleware.telemetry import setup_tracing, shutdown_tracing
from app.routes import auth, health

_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # startup — initialise clients here in future tasks (Redis, Qdrant…)
    yield
    # shutdown
    shutdown_tracing()


app = FastAPI(
    title=_settings.app_name,
    version=_settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# OTel must be set up after app creation so FastAPIInstrumentor can patch routes
setup_tracing(app, _settings)

app.include_router(health.router)
app.include_router(auth.router, prefix="/auth")
