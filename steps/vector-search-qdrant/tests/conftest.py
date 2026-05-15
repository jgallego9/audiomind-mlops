"""Shared fixtures for vector-search-qdrant step tests."""

import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_client import AsyncQdrantClient

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
    """Return a mock AsyncQdrantClient whose search returns one hit."""
    client = MagicMock(spec=AsyncQdrantClient)
    hit = MagicMock()
    hit.id = "doc-1"
    hit.score = 0.95
    hit.payload = {"text": "hello world"}
    client.search = AsyncMock(return_value=[hit])
    return client


@pytest.fixture()
def step(mock_qdrant: MagicMock):
    """Return a VectorSearchQdrantStep with a mocked Qdrant client."""
    from app.config import Settings
    from app.step import VectorSearchQdrantStep

    return VectorSearchQdrantStep(Settings(), client=mock_qdrant)
