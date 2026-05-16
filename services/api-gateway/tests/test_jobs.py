"""Tests for /transcribe and /jobs/{job_id} endpoints."""

import json
from datetime import UTC, datetime

from fakeredis.aioredis import FakeRedis
from httpx import AsyncClient


async def test_transcribe_returns_202_with_job_id(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        "/transcribe", json={"audio_url": "https://example.com/audio.mp3"}
    )
    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    assert body["status"] == "pending"
    assert "created_at" in body


async def test_transcribe_stores_job_in_redis(
    auth_client: AsyncClient, fake_redis: FakeRedis
) -> None:
    # When
    response = await auth_client.post(
        "/transcribe",
        json={"audio_url": "https://example.com/audio.mp3", "language": "es"},
    )
    job_id = response.json()["job_id"]

    # Then
    data = await fake_redis.hgetall(f"moiraweave:job:{job_id}")
    assert data["status"] == "pending"
    assert data["language"] == "es"
    assert data["user"] == "testuser"


async def test_transcribe_publishes_to_stream(
    auth_client: AsyncClient, fake_redis: FakeRedis
) -> None:
    # When
    await auth_client.post(
        "/transcribe", json={"audio_url": "https://example.com/audio.mp3"}
    )

    # Then
    messages = await fake_redis.xrange("moiraweave:jobs")
    assert len(messages) == 1
    _msg_id, fields = messages[0]
    assert fields["type"] == "transcribe"
    assert fields["user"] == "testuser"


async def test_transcribe_invalid_url_returns_422(auth_client: AsyncClient) -> None:
    response = await auth_client.post("/transcribe", json={"audio_url": "not-a-url"})
    assert response.status_code == 422


async def test_transcribe_no_auth_returns_4xx(client: AsyncClient) -> None:
    response = await client.post(
        "/transcribe", json={"audio_url": "https://example.com/audio.mp3"}
    )
    assert response.status_code in {401, 403}


async def test_get_job_returns_pending_status(
    auth_client: AsyncClient, fake_redis: FakeRedis
) -> None:
    # Given: a freshly submitted job
    create = await auth_client.post(
        "/transcribe", json={"audio_url": "https://example.com/audio.mp3"}
    )
    job_id = create.json()["job_id"]

    # When
    response = await auth_client.get(f"/jobs/{job_id}")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "pending"


async def test_get_job_completed_includes_result(
    auth_client: AsyncClient, fake_redis: FakeRedis
) -> None:
    # Given: a completed job seeded directly in Redis
    job_id = "completed-job-1"
    result_data = {"transcript": "hello world", "language": "en"}
    await fake_redis.hset(
        f"moiraweave:job:{job_id}",
        mapping={
            "status": "completed",
            "audio_url": "https://example.com/audio.mp3",
            "language": "en",
            "user": "testuser",
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "result": json.dumps(result_data),
        },
    )

    # When
    response = await auth_client.get(f"/jobs/{job_id}")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["result"]["transcript"] == "hello world"


async def test_get_job_not_found_returns_404(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/jobs/does-not-exist")
    assert response.status_code == 404


async def test_get_job_other_users_job_returns_403(
    auth_client: AsyncClient, fake_redis: FakeRedis
) -> None:
    # Given: a job owned by a different user
    job_id = "other-users-job"
    await fake_redis.hset(
        f"moiraweave:job:{job_id}",
        mapping={
            "status": "pending",
            "audio_url": "https://example.com/audio.mp3",
            "language": "en",
            "user": "other-user",
            "created_at": datetime.now(UTC).isoformat(),
        },
    )

    # When / Then
    response = await auth_client.get(f"/jobs/{job_id}")
    assert response.status_code == 403
