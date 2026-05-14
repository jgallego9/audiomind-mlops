# conftest.py Template

Replace `<SVC>`, `<REQUIRED_ENV_VAR>`, and dependency names to match the service.

```python
"""Shared fixtures for <SVC> tests."""

import os
import pathlib
import sys
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from qdrant_client import AsyncQdrantClient

# ---------------------------------------------------------------------------
# sys.path: ensure this service root resolves first so `app.*` maps here,
# not to another service when running the full monorepo suite together.
# ---------------------------------------------------------------------------
_SERVICE_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
for _k in list(sys.modules):
    if _k == "app" or _k.startswith("app."):
        del sys.modules[_k]
if _SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _SERVICE_ROOT)

# Set required env vars BEFORE any app module is imported.
os.environ.setdefault("<REQUIRED_ENV_VAR>", "<test-value>")
os.environ.setdefault("OTEL_ENABLED", "false")

# App imports come AFTER env vars.
from app.config import get_settings          # noqa: E402
from app.dependencies.auth import get_current_user  # noqa: E402
from app.dependencies.qdrant import get_qdrant      # noqa: E402
from app.dependencies.redis import get_redis        # noqa: E402
from app.main import app                     # noqa: E402
from app.models.auth import TokenData        # noqa: E402


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None]:
    """Isolate Settings between tests (get_settings uses @lru_cache)."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_redis() -> FakeRedis:
    """In-memory Redis compatible with redis.asyncio — no infrastructure."""
    return FakeRedis(decode_responses=True)


@pytest.fixture
def mock_qdrant() -> MagicMock:
    """Spec-checked AsyncQdrantClient stub."""
    client = MagicMock(spec=AsyncQdrantClient)
    client.query           = AsyncMock(return_value=[])
    client.add             = AsyncMock(return_value=["test-id"])
    client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    client.close           = AsyncMock()
    client.set_model       = MagicMock()  # sync
    return client


@pytest.fixture
def fake_user() -> TokenData:
    return TokenData(subject="testuser")


@pytest.fixture
async def client(
    fake_redis: FakeRedis,
    mock_qdrant: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Unauthenticated test client.

    ASGITransport does not trigger ASGI lifespan, so dependencies are
    injected directly into app.state and via dependency_overrides.
    """
    app.state.redis  = fake_redis
    app.state.qdrant = mock_qdrant
    app.dependency_overrides[get_redis]   = lambda: fake_redis
    app.dependency_overrides[get_qdrant]  = lambda: mock_qdrant
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        for attr in ("redis", "qdrant"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)


@pytest.fixture
async def auth_client(
    client: AsyncClient,
    fake_user: TokenData,
) -> AsyncGenerator[AsyncClient]:
    """Authenticated client — composes on client, adds only auth override."""
    app.dependency_overrides[get_current_user] = lambda: fake_user
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
```
