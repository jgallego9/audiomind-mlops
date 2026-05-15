"""Shared fixtures for worker tests."""

import os
import pathlib
import sys
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis.aioredis import FakeRedis
from qdrant_client import AsyncQdrantClient

# ---------------------------------------------------------------------------
# sys.path: ensure this service's root is first so `app.*` resolves to the
# worker service, not to api-gateway when running all tests together.
# ---------------------------------------------------------------------------
_SERVICE_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
for _k in list(sys.modules):
    if _k == "app" or _k.startswith("app."):
        del sys.modules[_k]
if _SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _SERVICE_ROOT)

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import app.consumer as _consumer_module  # noqa: E402
from app.config import Settings, get_settings  # noqa: E402

# Snapshot of ALL app.* modules loaded at conftest import time (worker's).
# Used by _restore_worker_app to re-populate sys.modules before each test so
# that patch("app.consumer.xxx") resolves to the worker, not the step.
_WORKER_APP_MODULES: dict[str, object] = {
    k: v for k, v in sys.modules.items() if k == "app" or k.startswith("app.")
}


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _restore_worker_app() -> None:
    """Re-populate sys.modules with the worker's app.* before each test.

    pytest collects tests from multiple services in one pass.  The step
    conftest clears app.* and adds the step root during collection, so by
    the time worker tests run sys.modules["app"] may point to the step.
    Restoring the snapshot ensures patch("app.consumer.xxx") resolves here.
    """
    sys.modules.update(_WORKER_APP_MODULES)


@pytest.fixture
def worker_settings() -> Settings:
    return Settings(
        redis_url="redis://localhost:6379/0",  # type: ignore[arg-type]
        qdrant_collection="test-transcriptions",
        embedding_model="BAAI/bge-small-en-v1.5",
    )


@pytest.fixture(autouse=True)
def _mock_mlflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent real MLflow HTTP calls during unit tests."""
    monkeypatch.setattr(
        _consumer_module,
        "log_inference_metrics",
        AsyncMock(return_value=None),
    )


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis(decode_responses=True)


@pytest.fixture
def mock_qdrant() -> MagicMock:
    client = MagicMock(spec=AsyncQdrantClient)
    client.add = AsyncMock(return_value=["id-1"])
    client.query = AsyncMock(return_value=[])
    client.close = AsyncMock()
    client.set_model = MagicMock()
    return client
