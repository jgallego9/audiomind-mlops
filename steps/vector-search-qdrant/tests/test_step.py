"""Tests for the vector-search-qdrant step."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from moiraweave_step_sdk.models import InferRequest, Tensor


@pytest.fixture()
def client(step) -> None:
    """Return a TestClient wired to the step's FastAPI app."""
    return TestClient(step.build_app())


def test_step_name(step) -> None:
    assert step.name == "vector-search-qdrant"


def test_step_task(step) -> None:
    assert step.task == "vector-search"


def test_step_implementation(step) -> None:
    assert step.implementation == "qdrant"


async def test_predict_returns_results(
    step,
    mock_qdrant: MagicMock,
) -> None:
    """predict() returns a JSON-encoded list of search results."""
    request = InferRequest(
        model_name="vector-search-qdrant",
        inputs=[
            Tensor(
                name="vector", datatype="FP32", shape=[4], data=[0.1, 0.2, 0.3, 0.4]
            ),
            Tensor(name="top_k", datatype="INT64", shape=[1], data=[3]),
        ],
    )
    response = await step.predict(request)

    mock_qdrant.search.assert_awaited_once()
    call_kwargs = mock_qdrant.search.call_args.kwargs
    assert call_kwargs["limit"] == 3

    assert len(response.outputs) == 1
    results = json.loads(response.outputs[0].data[0])
    assert results[0]["id"] == "doc-1"
    assert results[0]["score"] == pytest.approx(0.95)
    assert results[0]["metadata"] == {"text": "hello world"}


async def test_predict_uses_default_top_k(
    step,
    mock_qdrant: MagicMock,
) -> None:
    """predict() uses settings.default_top_k when top_k tensor is absent."""
    request = InferRequest(
        model_name="vector-search-qdrant",
        inputs=[
            Tensor(
                name="vector", datatype="FP32", shape=[4], data=[0.1, 0.2, 0.3, 0.4]
            ),
        ],
    )
    await step.predict(request)

    call_kwargs = mock_qdrant.search.call_args.kwargs
    assert call_kwargs["limit"] == 5  # default_top_k


async def test_predict_missing_vector_raises(
    step,
) -> None:
    """predict() raises ValueError when the vector tensor is missing."""
    request = InferRequest(
        model_name="vector-search-qdrant",
        inputs=[],
    )
    with pytest.raises(ValueError, match="vector"):
        await step.predict(request)


async def test_predict_passes_filter(
    step,
    mock_qdrant: MagicMock,
) -> None:
    """predict() forwards a non-empty filters tensor to Qdrant."""
    filters = json.dumps({"must": [{"key": "lang", "match": {"value": "en"}}]})
    request = InferRequest(
        model_name="vector-search-qdrant",
        inputs=[
            Tensor(
                name="vector", datatype="FP32", shape=[4], data=[0.1, 0.2, 0.3, 0.4]
            ),
            Tensor(name="filters", datatype="BYTES", shape=[1], data=[filters]),
        ],
    )
    await step.predict(request)

    call_kwargs = mock_qdrant.search.call_args.kwargs
    assert call_kwargs["query_filter"] is not None


def test_health_ready(client: TestClient) -> None:
    """GET /v2/health/ready returns 200."""
    assert client.get("/v2/health/ready").status_code == 200


def test_model_metadata(client: TestClient) -> None:
    """GET /v2/models/vector-search-qdrant returns correct metadata."""
    resp = client.get("/v2/models/vector-search-qdrant")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "vector-search-qdrant"
    assert data["task"] == "vector-search"
    assert any(t["name"] == "vector" for t in data["inputs"])
    assert any(t["name"] == "results" for t in data["outputs"])


def test_create_app_returns_fastapi() -> None:
    """create_app() returns a FastAPI instance."""
    with patch("app.step.AsyncQdrantClient"):
        from app.main import create_app

        assert isinstance(create_app(), FastAPI)
