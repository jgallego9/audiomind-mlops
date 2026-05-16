"""Tests for GET /v1/pipelines and POST /v1/pipelines/{id}/jobs."""

import json
from unittest.mock import patch

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import AsyncClient
from moiraweave_shared.pipeline import PipelineDefinition


def _audio_rag_pipeline() -> PipelineDefinition:
    return PipelineDefinition.model_validate(
        {
            "name": "audio-rag",
            "version": "1.0",
            "description": "test pipeline",
            "trigger": {"type": "redis-stream", "stream": "pipelines:audio-rag:jobs"},
            "steps": [
                {
                    "id": "transcribe",
                    "task": "audio-transcribe",
                    "url": "http://audio-transcribe-whisper:8000",
                }
            ],
        }
    )


@pytest.fixture
def _patch_load_pipelines():
    """Patch moiraweave_shared.pipeline.load_pipelines everywhere it's imported."""
    with (
        patch(
            "app.routes.pipelines.load_pipelines",
            return_value=[_audio_rag_pipeline()],
        ) as mock,
    ):
        yield mock


# ---------------------------------------------------------------------------
# GET /v1/pipelines
# ---------------------------------------------------------------------------


async def test_list_pipelines_returns_pipeline(
    _patch_load_pipelines, client: AsyncClient
) -> None:
    resp = await client.get("/v1/pipelines")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    item = body[0]
    assert item["id"] == "audio-rag"
    assert item["name"] == "audio-rag"
    assert item["stream"] == "pipelines:audio-rag:jobs"
    assert item["steps"][0]["id"] == "transcribe"
    assert item["steps"][0]["task"] == "audio-transcribe"


async def test_list_pipelines_returns_empty_on_error(client: AsyncClient) -> None:
    with patch("app.routes.pipelines.load_pipelines", side_effect=Exception("boom")):
        resp = await client.get("/v1/pipelines")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /v1/pipelines/{id}/jobs
# ---------------------------------------------------------------------------


async def test_submit_job_returns_202(
    _patch_load_pipelines, auth_client: AsyncClient, fake_redis: FakeRedis
) -> None:
    resp = await auth_client.post(
        "/v1/pipelines/audio-rag/jobs",
        json={"payload": {"audio_url": "http://example.com/audio.mp3"}},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert body["pipeline_id"] == "audio-rag"
    assert body["status"] == "pending"
    assert "created_at" in body


async def test_submit_job_stores_status_in_redis(
    _patch_load_pipelines, auth_client: AsyncClient, fake_redis: FakeRedis
) -> None:
    resp = await auth_client.post(
        "/v1/pipelines/audio-rag/jobs",
        json={"payload": {"audio_url": "http://example.com/audio.mp3"}},
    )
    job_id = resp.json()["job_id"]
    status = await fake_redis.hget(f"pipeline:job:{job_id}", "status")
    assert status == "pending"


async def test_submit_job_publishes_to_stream(
    _patch_load_pipelines, auth_client: AsyncClient, fake_redis: FakeRedis
) -> None:
    await auth_client.post(
        "/v1/pipelines/audio-rag/jobs",
        json={"payload": {"audio_url": "http://example.com/audio.mp3"}},
    )
    entries = await fake_redis.xrange("pipelines:audio-rag:jobs")
    assert len(entries) == 1
    _msg_id, fields = entries[0]
    assert fields["pipeline_id"] == "audio-rag"
    # payload must be valid JSON
    parsed = json.loads(fields["payload"])
    assert parsed["audio_url"] == "http://example.com/audio.mp3"


async def test_submit_job_unknown_pipeline_returns_404(
    _patch_load_pipelines, auth_client: AsyncClient
) -> None:
    resp = await auth_client.post(
        "/v1/pipelines/unknown-pipeline/jobs",
        json={"payload": {}},
    )
    assert resp.status_code == 404


async def test_submit_job_requires_auth(
    _patch_load_pipelines, client: AsyncClient
) -> None:
    resp = await client.post(
        "/v1/pipelines/audio-rag/jobs",
        json={"payload": {}},
    )
    assert resp.status_code == 401
