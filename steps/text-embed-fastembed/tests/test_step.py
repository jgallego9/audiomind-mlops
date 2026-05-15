"""Tests for the text-embed-fastembed step."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from inferflow_step_sdk.models import InferRequest, Tensor


@pytest.fixture()
def client(step) -> None:
    """Return a TestClient wired to the step's FastAPI app."""
    return TestClient(step.build_app())


def test_step_name(step) -> None:
    assert step.name == "text-embed-fastembed"


def test_step_task(step) -> None:
    assert step.task == "text-embed"


def test_step_implementation(step) -> None:
    assert step.implementation == "fastembed"


def test_step_version(step) -> None:
    assert step.version == "1"


async def test_predict_returns_embedding(
    step,
    mock_model: MagicMock,
) -> None:
    """predict() returns a FP32 embedding tensor with the correct values."""
    mock_model.embed.return_value = iter(
        [np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)]
    )
    request = InferRequest(
        model_name="text-embed-fastembed",
        inputs=[Tensor(name="text", datatype="BYTES", shape=[1], data=["hello world"])],
    )
    response = await step.predict(request)

    assert len(response.outputs) == 1
    tensor = response.outputs[0]
    assert tensor.name == "embedding"
    assert tensor.datatype == "FP32"
    assert len(tensor.data) == 4
    assert abs(tensor.data[0] - 0.1) < 1e-5


async def test_predict_missing_text_raises(
    step,
) -> None:
    """predict() raises ValueError when the text tensor is absent."""
    request = InferRequest(
        model_name="text-embed-fastembed",
        inputs=[],
    )
    with pytest.raises(ValueError, match="text"):
        await step.predict(request)


def test_v2_infer_endpoint(client: TestClient) -> None:
    """POST /v2/models/text-embed-fastembed/infer returns 200 with embedding."""
    payload = {
        "inputs": [{"name": "text", "datatype": "BYTES", "shape": [1], "data": ["hi"]}]
    }
    resp = client.post("/v2/models/text-embed-fastembed/infer", json=payload)
    assert resp.status_code == 200
    outputs = resp.json()["outputs"]
    assert outputs[0]["name"] == "embedding"
    assert outputs[0]["datatype"] == "FP32"


def test_health_ready(client: TestClient) -> None:
    """GET /v2/health/ready returns 200."""
    assert client.get("/v2/health/ready").status_code == 200


def test_model_metadata(client: TestClient) -> None:
    """GET /v2/models/text-embed-fastembed returns correct metadata."""
    resp = client.get("/v2/models/text-embed-fastembed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "text-embed-fastembed"
    assert data["task"] == "text-embed"
    assert any(t["name"] == "text" for t in data["inputs"])
    assert any(t["name"] == "embedding" for t in data["outputs"])


def test_create_app_returns_fastapi() -> None:
    """create_app() returns a FastAPI instance."""
    with patch("app.step.TextEmbedding"):
        from app.main import create_app

        assert isinstance(create_app(), FastAPI)
