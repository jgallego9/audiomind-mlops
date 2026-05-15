from unittest.mock import AsyncMock, patch

import pytest
from httpx import Request, Response
from inferflow_step_sdk.models import InferRequest, Tensor

from app.config import Settings
from app.step import AudioTranscribeWhisperStep, _get_bytes_tensor


@pytest.fixture()
def settings() -> Settings:
    return Settings(whisper_url="http://whisper-test:9000")


@pytest.fixture()
def step(settings: Settings) -> AudioTranscribeWhisperStep:
    return AudioTranscribeWhisperStep(settings)


@pytest.fixture()
def infer_request() -> InferRequest:
    return InferRequest(
        id="test-id",
        inputs=[
            Tensor(name="audio_url", shape=[1], datatype="BYTES", data=["http://example.com/audio.mp3"]),
            Tensor(name="language", shape=[1], datatype="BYTES", data=["en"]),
        ],
    )


@pytest.fixture()
def infer_request_auto_language() -> InferRequest:
    return InferRequest(
        id="test-id-auto",
        inputs=[
            Tensor(name="audio_url", shape=[1], datatype="BYTES", data=["http://example.com/audio.mp3"]),
        ],
    )


def _make_response(status_code: int, content: bytes | None = None, json_data: dict | None = None) -> Response:
    """Build a minimal httpx.Response for mocking."""
    if json_data is not None:
        import json
        content = json.dumps(json_data).encode()
    req = Request("GET", "http://mock.test/")
    return Response(status_code=status_code, content=content or b"", request=req)


# ---------------------------------------------------------------------------
# BaseStep properties
# ---------------------------------------------------------------------------

def test_step_name(step: AudioTranscribeWhisperStep) -> None:
    assert step.name == "audio-transcribe-whisper"


def test_step_version(step: AudioTranscribeWhisperStep) -> None:
    assert step.version == "1"


# ---------------------------------------------------------------------------
# predict — happy path with explicit language
# ---------------------------------------------------------------------------

async def test_predict_with_language(
    step: AudioTranscribeWhisperStep,
    infer_request: InferRequest,
) -> None:
    audio_bytes = b"fake-audio"
    whisper_json = {"text": "Hello world", "language": "en", "duration": 3.5}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_make_response(200, content=audio_bytes))
    mock_client.post = AsyncMock(return_value=_make_response(200, json_data=whisper_json))

    with patch("app.step.httpx.AsyncClient", return_value=mock_client):
        response = await step.predict(infer_request)

    assert response.model_name == "audio-transcribe-whisper"
    assert response.id == "test-id"

    outputs = {t.name: t for t in response.outputs}
    assert outputs["transcript"].data == ["Hello world"]
    assert outputs["language"].data == ["en"]
    assert outputs["duration"].data == [3.5]


# ---------------------------------------------------------------------------
# predict — auto language (no language tensor, Whisper detects it)
# ---------------------------------------------------------------------------

async def test_predict_auto_language(
    step: AudioTranscribeWhisperStep,
    infer_request_auto_language: InferRequest,
) -> None:
    whisper_json = {"text": "Hola mundo", "language": "es", "duration": 2.0}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_make_response(200, content=b"audio"))
    mock_client.post = AsyncMock(return_value=_make_response(200, json_data=whisper_json))

    with patch("app.step.httpx.AsyncClient", return_value=mock_client):
        response = await step.predict(infer_request_auto_language)

    outputs = {t.name: t for t in response.outputs}
    assert outputs["language"].data == ["es"]

    # Verify that no 'language' param was sent to Whisper (auto = omitted)
    call_kwargs = mock_client.post.call_args.kwargs
    assert "language" not in call_kwargs.get("params", {})


# ---------------------------------------------------------------------------
# predict — Whisper returns empty duration field
# ---------------------------------------------------------------------------

async def test_predict_missing_duration(
    step: AudioTranscribeWhisperStep,
    infer_request: InferRequest,
) -> None:
    whisper_json = {"text": "Test", "language": "en"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=_make_response(200, content=b"audio"))
    mock_client.post = AsyncMock(return_value=_make_response(200, json_data=whisper_json))

    with patch("app.step.httpx.AsyncClient", return_value=mock_client):
        response = await step.predict(infer_request)

    outputs = {t.name: t for t in response.outputs}
    assert outputs["duration"].data == [0.0]


# ---------------------------------------------------------------------------
# _get_bytes_tensor helper
# ---------------------------------------------------------------------------

def test_get_bytes_tensor_found() -> None:
    req = InferRequest(
        inputs=[Tensor(name="foo", shape=[1], datatype="BYTES", data=["bar"])]
    )
    assert _get_bytes_tensor(req, "foo") == "bar"


def test_get_bytes_tensor_default() -> None:
    req = InferRequest(inputs=[])
    assert _get_bytes_tensor(req, "missing", default="fallback") == "fallback"


def test_get_bytes_tensor_raises_without_default() -> None:
    req = InferRequest(inputs=[])
    with pytest.raises(ValueError, match="Required input tensor 'missing' not found"):
        _get_bytes_tensor(req, "missing")


# ---------------------------------------------------------------------------
# create_app smoke test
# ---------------------------------------------------------------------------

def test_create_app_returns_fastapi() -> None:
    from fastapi import FastAPI

    from app.main import create_app

    with patch("app.main.Settings", return_value=Settings(whisper_url="http://x:9000")):
        application = create_app()

    assert isinstance(application, FastAPI)
