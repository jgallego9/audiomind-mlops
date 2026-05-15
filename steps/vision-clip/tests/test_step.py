"""Tests for the vision-clip step."""

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
    assert step.name == "vision-clip"


def test_step_task(step) -> None:
    assert step.task == "image-embed"


def test_step_implementation(step) -> None:
    assert step.implementation == "clip"


def test_step_version(step) -> None:
    assert step.version == "1"


async def test_predict_returns_embedding(
    step,
    mock_model: MagicMock,
) -> None:
    """predict() returns a FP32 embedding tensor with the correct values."""
    mock_model.embed.return_value = iter([np.array([0.9, 0.8, 0.7], dtype=np.float32)])
    request = InferRequest(
        model_name="vision-clip",
        inputs=[
            Tensor(
                name="image_url",
                datatype="BYTES",
                shape=[1],
                data=["https://example.com/dog.png"],
            )
        ],
    )

    response = await step.predict(request)

    assert len(response.outputs) == 1
    tensor = response.outputs[0]
    assert tensor.name == "embedding"
    assert tensor.datatype == "FP32"
    assert tensor.shape == [3]
    assert abs(tensor.data[0] - 0.9) < 1e-5


async def test_predict_missing_image_raises(step) -> None:
    """predict() raises ValueError when image_url tensor is absent."""
    request = InferRequest(
        model_name="vision-clip",
        inputs=[],
    )
    with pytest.raises(ValueError, match="image_url"):
        await step.predict(request)


def test_v2_infer_endpoint(client: TestClient) -> None:
    """POST /v2/models/vision-clip/infer returns 200 with embedding."""
    payload = {
        "inputs": [
            {
                "name": "image_url",
                "datatype": "BYTES",
                "shape": [1],
                "data": ["https://example.com/cat.png"],
            }
        ]
    }
    resp = client.post("/v2/models/vision-clip/infer", json=payload)
    assert resp.status_code == 200
    outputs = resp.json()["outputs"]
    assert outputs[0]["name"] == "embedding"
    assert outputs[0]["datatype"] == "FP32"


def test_health_ready(client: TestClient) -> None:
    """GET /v2/health/ready returns 200."""
    assert client.get("/v2/health/ready").status_code == 200


def test_model_metadata(client: TestClient) -> None:
    """GET /v2/models/vision-clip returns correct metadata."""
    resp = client.get("/v2/models/vision-clip")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "vision-clip"
    assert data["task"] == "image-embed"
    assert any(t["name"] == "image_url" for t in data["inputs"])
    assert any(t["name"] == "embedding" for t in data["outputs"])


def test_create_app_returns_fastapi() -> None:
    """create_app() returns a FastAPI instance."""
    with patch("app.step.ImageEmbedding"):
        from app.main import create_app

        assert isinstance(create_app(), FastAPI)
