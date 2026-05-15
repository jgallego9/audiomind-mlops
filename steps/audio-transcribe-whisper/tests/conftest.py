"""Shared fixtures for audio-transcribe-whisper step tests."""

import pathlib
import sys

import pytest

# Ensure `app.*` resolves to this step, not to api-gateway/worker which are
# collected first.  Clear any previously cached `app` namespace, then
# prepend the step root so it wins the import race.
_STEP_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
for _k in list(sys.modules):
    if _k == "app" or _k.startswith("app."):
        del sys.modules[_k]
if _STEP_ROOT not in sys.path:
    sys.path.insert(0, _STEP_ROOT)


@pytest.fixture(autouse=True)
def _restore_step_app() -> None:
    """Restore step's app.* in sys.modules before each test.

    Worker conftest's _restore_worker_app mutates sys.modules["app"] to point
    to the worker for every worker test.  Clear and re-import from the step
    root (which is first in sys.path after collection) so that intra-test
    imports like ``from app.main import create_app`` find the correct module.
    """
    # Ensure this step's root is first in sys.path
    if not sys.path or sys.path[0] != _STEP_ROOT:
        sys.path.insert(0, _STEP_ROOT)
    for _k in list(sys.modules):
        if _k == "app" or _k.startswith("app."):
            del sys.modules[_k]
    import app  # noqa: F401
    import app.config  # noqa: F401
    import app.main  # noqa: F401
    import app.step  # noqa: F401

