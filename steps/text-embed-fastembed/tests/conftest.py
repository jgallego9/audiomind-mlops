"""Shared fixtures for text-embed-fastembed step tests."""

import pathlib
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

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
def mock_model() -> MagicMock:
    """Return a mock FastEmbed TextEmbedding that returns a fixed 4-dim vector."""
    model = MagicMock()
    model.embed.return_value = iter([np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)])
    return model


@pytest.fixture()
def step(mock_model: MagicMock):
    """Return a TextEmbedFastEmbedStep with a mocked FastEmbed model."""
    with patch("app.step.TextEmbedding", return_value=mock_model):
        from app.config import Settings
        from app.step import TextEmbedFastEmbedStep

        return TextEmbedFastEmbedStep(Settings())
