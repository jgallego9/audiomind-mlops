"""Tests for the vector-index-qdrant step."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from inferflow_step_sdk.models import InferRequest, Tensor
from qdrant_client.http.models import CollectionsResponse


@pytest.fixture()
def client(step) -> None:
    """Return a TestClient wired to the step's FastAPI app."""
    return TestClient(step.build_app())


def test_step_name(step) -> None:
    assert step.name == "vector-index-qdrant"


def test_step_task(step) -> None:
    assert step.task == "vector-index"


def test_step_implementation(step) -> None:
    assert step.implementation == "qdrant"


async def test_predict_indexes_vector(
    step,
    mock_qdrant: MagicMock,
) -> None:
    """predict() upserts the vector and returns indexed=True."""
    request = InferRequest(
        model_name="vector-index-qdrant",
        inputs=[
            Tensor(name="id", datatype="BYTES", shape=[1], data=["doc-1"]),
            Tensor(
                name="vector", datatype="FP32", shape=[4], data=[0.1, 0.2, 0.3, 0.4]
            ),
            Tensor(
                name="metadata",
                datatype="BYTES",
                shape=[1],
                data=[json.dumps({"text": "hello"})],
            ),
        ],
    )
    response = await step.predict(request)

    mock_qdrant.upsert.assert_awaited_once()
    assert response.outputs[0].name == "indexed"
    assert response.outputs[0].data == [True]


async def test_predict_creates_collection_when_missing(
    step,
    mock_qdrant: MagicMock,
) -> None:
    """predict() calls create_collection when the collection does not exist."""
    request = InferRequest(
        model_name="vector-index-qdrant",
        inputs=[
            Tensor(name="id", datatype="BYTES", shape=[1], data=["doc-2"]),
            Tensor(
                name="vector", datatype="FP32", shape=[4], data=[0.1, 0.2, 0.3, 0.4]
            ),
        ],
    )
    await step.predict(request)

    mock_qdrant.create_collection.assert_awaited_once()


async def test_predict_skips_create_when_collection_exists(
    mock_qdrant: MagicMock,
) -> None:
    """predict() does not call create_collection when the collection exists."""
    from app.config import Settings
    from app.step import VectorIndexQdrantStep

    existing = MagicMock()
    existing.name = "transcriptions"
    collections_resp = MagicMock(spec=CollectionsResponse)
    collections_resp.collections = [existing]
    mock_qdrant.get_collections = AsyncMock(return_value=collections_resp)

    step = VectorIndexQdrantStep(Settings(), client=mock_qdrant)
    request = InferRequest(
        model_name="vector-index-qdrant",
        inputs=[
            Tensor(name="id", datatype="BYTES", shape=[1], data=["doc-3"]),
            Tensor(
                name="vector", datatype="FP32", shape=[4], data=[0.1, 0.2, 0.3, 0.4]
            ),
        ],
    )
    await step.predict(request)

    mock_qdrant.create_collection.assert_not_called()


async def test_predict_missing_id_raises(
    step,
) -> None:
    """predict() raises ValueError when the id tensor is missing."""
    request = InferRequest(
        model_name="vector-index-qdrant",
        inputs=[
            Tensor(
                name="vector", datatype="FP32", shape=[4], data=[0.1, 0.2, 0.3, 0.4]
            ),
        ],
    )
    with pytest.raises(ValueError, match="id"):
        await step.predict(request)


def test_health_ready(client: TestClient) -> None:
    """GET /v2/health/ready returns 200."""
    assert client.get("/v2/health/ready").status_code == 200


def test_model_metadata(client: TestClient) -> None:
    """GET /v2/models/vector-index-qdrant returns correct metadata."""
    resp = client.get("/v2/models/vector-index-qdrant")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "vector-index-qdrant"
    assert data["task"] == "vector-index"


def test_create_app_returns_fastapi() -> None:
    """create_app() returns a FastAPI instance."""
    with patch("app.step.AsyncQdrantClient"):
        from app.main import create_app

        assert isinstance(create_app(), FastAPI)
