"""Tests for inferflow_step_sdk BaseStep and KServe V2 models."""

import pytest
from fastapi.testclient import TestClient
from inferflow_step_sdk.base import BaseStep
from inferflow_step_sdk.models import InferRequest, InferResponse

# ---------------------------------------------------------------------------
# Minimal concrete step used across all tests
# ---------------------------------------------------------------------------


class EchoStep(BaseStep):
    """Returns the first input tensor unchanged."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def version(self) -> str:
        return "1"

    async def predict(self, request: InferRequest) -> InferResponse:
        return InferResponse(
            model_name=self.name,
            id=request.id,
            outputs=list(request.inputs),
        )


@pytest.fixture
def client() -> TestClient:
    app = EchoStep().build_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


def test_liveness_returns_live(client: TestClient) -> None:
    resp = client.get("/v2/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"live": True}


def test_server_ready_returns_live(client: TestClient) -> None:
    resp = client.get("/v2/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"live": True}


def test_model_ready_returns_ready(client: TestClient) -> None:
    resp = client.get("/v2/models/echo/ready")
    assert resp.status_code == 200
    assert resp.json() == {"name": "echo", "ready": True}


def test_model_ready_unknown_model_returns_404(client: TestClient) -> None:
    resp = client.get("/v2/models/unknown/ready")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Inference endpoint
# ---------------------------------------------------------------------------


def test_infer_echoes_input(client: TestClient) -> None:
    payload = {
        "id": "req-1",
        "inputs": [
            {"name": "text", "shape": [1], "datatype": "BYTES", "data": ["hello"]}
        ],
    }
    resp = client.post("/v2/models/echo/infer", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_name"] == "echo"
    assert body["id"] == "req-1"
    assert body["outputs"][0]["name"] == "text"
    assert body["outputs"][0]["data"] == ["hello"]


def test_infer_unknown_model_returns_404(client: TestClient) -> None:
    payload = {
        "inputs": [{"name": "x", "shape": [1], "datatype": "BYTES", "data": ["y"]}]
    }
    resp = client.post("/v2/models/wrong/infer", json=payload)
    assert resp.status_code == 404


def test_infer_without_id_omits_id_field(client: TestClient) -> None:
    payload = {
        "inputs": [{"name": "x", "shape": [1], "datatype": "FP32", "data": [1.0]}]
    }
    resp = client.post("/v2/models/echo/infer", json=payload)
    assert resp.status_code == 200
    assert resp.json()["id"] is None


# ---------------------------------------------------------------------------
# Custom is_ready override
# ---------------------------------------------------------------------------


class NotReadyStep(EchoStep):
    @property
    def name(self) -> str:
        return "not-ready"

    async def is_ready(self) -> bool:
        return False


def test_not_ready_step_returns_false() -> None:
    app = NotReadyStep().build_app()
    c = TestClient(app)
    assert c.get("/v2/health/ready").json() == {"live": False}
    assert c.get("/v2/models/not-ready/ready").json() == {
        "name": "not-ready",
        "ready": False,
    }


# ---------------------------------------------------------------------------
# Model metadata endpoint (KServe V2 GET /v2/models/{name})
# ---------------------------------------------------------------------------


def test_model_metadata_returns_correct_response(client: TestClient) -> None:
    resp = client.get("/v2/models/echo")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "echo"
    assert body["platform"] == "inferflow"
    assert body["versions"] == ["1"]
    assert body["task"] == ""
    assert body["implementation"] == ""
    assert body["inputs"] == []
    assert body["outputs"] == []


def test_model_metadata_unknown_model_returns_404(client: TestClient) -> None:
    resp = client.get("/v2/models/unknown")
    assert resp.status_code == 404
