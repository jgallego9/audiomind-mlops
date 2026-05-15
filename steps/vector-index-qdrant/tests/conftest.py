"""Shared fixtures for vector-index-qdrant step tests."""

import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import CollectionsResponse

_STEP_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
for _k in list(sys.modules):
    if _k == "app" or _k.startswith("app."):
        del sys.modules[_k]
if _STEP_ROOT not in sys.path:
    sys.path.insert(0, _STEP_ROOT)


@pytest.fixture(autouse=True)
def _restore_step_app() -> None:
    """Restore step's app.* in sys.modules before each test."""
    # Ensure this step's root is first in sys.path
    if not sys.path or sys.path[0] != _STEP_ROOT:
        sys.path.insert(0, _STEP_ROOT)
    for _k in list(sys.modules):
        if _k == "app" or _k.startswith("app."):
            del sys.modules[_k]
    import app  # noqa: F401
    import app.config  # noqa: F401
    import app.step  # noqa: F401


@pytest.fixture()
def mock_qdrant() -> MagicMock:
    """Return a mock AsyncQdrantClient with collection already present."""
    client = MagicMock(spec=AsyncQdrantClient)
    collections_resp = MagicMock(spec=CollectionsResponse)
    collections_resp.collections = []
    client.get_collections = AsyncMock(return_value=collections_resp)
    client.create_collection = AsyncMock()
    client.upsert = AsyncMock()
    return client


@pytest.fixture()
def step(mock_qdrant: MagicMock):
    """Return a VectorIndexQdrantStep with a mocked Qdrant client."""
    from app.config import Settings
    from app.step import VectorIndexQdrantStep

    return VectorIndexQdrantStep(Settings(), client=mock_qdrant)
