from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler  # type: ignore[import-untyped]
from slowapi.errors import RateLimitExceeded  # type: ignore[import-untyped]

from app.config import settings
from app.middleware.rate_limit import limiter
from app.routes import auth, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # startup — initialise clients here in future tasks (Redis, Qdrant…)
    yield
    # shutdown — close clients here


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.include_router(health.router)
app.include_router(auth.router, prefix="/auth")
