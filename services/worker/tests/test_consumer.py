"""Tests for app.consumer (stream consumer loop helpers)."""

import asyncio
import contextlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis
from redis.exceptions import ResponseError

from app.config import Settings
from app.consumer import (
    _ensure_consumer_group,
    _process_message,
    _recover_pending,
    run_consumer,
)

_STREAM = "moiraweave:jobs"
_GROUP = "moiraweave:workers"
_JOB_PREFIX = "moiraweave:job"

_FAST_TRANSCRIPTION = {
    "transcript": "hello world",
    "language": "en",
    "duration": 1.0,
    "confidence": 0.99,
    "segments": [],
}


# ---------------------------------------------------------------------------
# _ensure_consumer_group
# ---------------------------------------------------------------------------


async def test_ensure_consumer_group_creates_group(
    fake_redis: FakeRedis, worker_settings: Settings
) -> None:
    await _ensure_consumer_group(fake_redis)
    groups = await fake_redis.xinfo_groups(_STREAM)
    assert any(g["name"] == _GROUP for g in groups)


async def test_ensure_consumer_group_ignores_busygroup(
    fake_redis: FakeRedis,
) -> None:
    """Calling twice should not raise even though BUSYGROUP is returned."""
    await _ensure_consumer_group(fake_redis)
    # Second call should be a no-op.
    await _ensure_consumer_group(fake_redis)


async def test_ensure_consumer_group_reraises_other_errors(
    fake_redis: FakeRedis,
) -> None:
    # Given: xgroup_create raises an unrelated ResponseError
    with (
        patch.object(
            fake_redis,
            "xgroup_create",
            AsyncMock(side_effect=ResponseError("WRONGTYPE")),
        ),
        # When / Then
        pytest.raises(ResponseError, match="WRONGTYPE"),
    ):
        await _ensure_consumer_group(fake_redis)


# ---------------------------------------------------------------------------
# _process_message
# ---------------------------------------------------------------------------


async def test_process_message_success(
    fake_redis: FakeRedis, mock_qdrant: MagicMock, worker_settings: Settings
) -> None:
    # Given: a pending job in Redis
    job_id = "job-success-1"
    await fake_redis.hset(
        f"{_JOB_PREFIX}:{job_id}",
        mapping={
            "status": "pending",
            "audio_url": "https://example.com/a.mp3",
            "language": "en",
            "user": "alice",
        },
    )

    # When
    with patch(
        "app.consumer.mock_transcribe", AsyncMock(return_value=_FAST_TRANSCRIPTION)
    ):
        await _process_message(
            fake_redis,
            mock_qdrant,
            worker_settings,
            "1-0",
            {
                "job_id": job_id,
                "audio_url": "https://example.com/a.mp3",
                "language": "en",
                "user": "alice",
            },
        )

    # Then
    data = await fake_redis.hgetall(f"{_JOB_PREFIX}:{job_id}")
    assert data["status"] == "completed"
    result = json.loads(data["result"])
    assert result["transcript"] == "hello world"


async def test_process_message_indexes_to_qdrant(
    fake_redis: FakeRedis, mock_qdrant: MagicMock, worker_settings: Settings
) -> None:
    # Given
    job_id = "job-idx-1"

    # When
    with patch(
        "app.consumer.mock_transcribe", AsyncMock(return_value=_FAST_TRANSCRIPTION)
    ):
        await _process_message(
            fake_redis,
            mock_qdrant,
            worker_settings,
            "1-0",
            {
                "job_id": job_id,
                "audio_url": "https://example.com/a.mp3",
                "language": "en",
                "user": "alice",
            },
        )

    # Then
    mock_qdrant.add.assert_awaited_once()
    call_kwargs = mock_qdrant.add.call_args.kwargs
    assert call_kwargs["ids"] == [job_id]


async def test_process_message_failure_sets_failed_status(
    fake_redis: FakeRedis, mock_qdrant: MagicMock, worker_settings: Settings
) -> None:
    # Given: transcription raises a runtime error
    job_id = "job-fail-1"

    # When
    with patch(
        "app.consumer.mock_transcribe", AsyncMock(side_effect=RuntimeError("bad audio"))
    ):
        await _process_message(
            fake_redis,
            mock_qdrant,
            worker_settings,
            "1-0",
            {
                "job_id": job_id,
                "audio_url": "bad-url",
                "language": "en",
                "user": "alice",
            },
        )

    # Then
    data = await fake_redis.hgetall(f"{_JOB_PREFIX}:{job_id}")
    assert data["status"] == "failed"
    assert "bad audio" in data["error"]


async def test_process_message_acknowledges_stream(
    fake_redis: FakeRedis, mock_qdrant: MagicMock, worker_settings: Settings
) -> None:
    # Given: a message delivered to a consumer group (enters PEL)
    await _ensure_consumer_group(fake_redis)
    _ = await fake_redis.xadd(_STREAM, {"job_id": "j1", "type": "transcribe"})
    msgs = await fake_redis.xreadgroup(
        groupname=_GROUP,
        consumername="w1",
        streams={_STREAM: ">"},
        count=1,
    )
    _, stream_msgs = msgs[0]
    actual_msg_id, fields = stream_msgs[0]

    # When: processing fails
    with patch(
        "app.consumer.mock_transcribe", AsyncMock(side_effect=RuntimeError("err"))
    ):
        await _process_message(
            fake_redis, mock_qdrant, worker_settings, actual_msg_id, dict(fields)
        )

    # Then: message must be ACKed even on failure
    pending = await fake_redis.xpending(_STREAM, _GROUP)
    assert pending["pending"] == 0


# ---------------------------------------------------------------------------
# _recover_pending
# ---------------------------------------------------------------------------


async def test_recover_pending_no_messages(
    fake_redis: FakeRedis, mock_qdrant: MagicMock, worker_settings: Settings
) -> None:
    """recover_pending should succeed silently when there are no stale messages."""
    await _ensure_consumer_group(fake_redis)
    # Should not raise.
    await _recover_pending(fake_redis, mock_qdrant, worker_settings, "consumer-1")


# ---------------------------------------------------------------------------
# run_consumer (integration — limited iterations)
# ---------------------------------------------------------------------------


async def test_run_consumer_processes_one_message(
    fake_redis: FakeRedis, mock_qdrant: MagicMock, worker_settings: Settings
) -> None:
    # Given: a pending job in Redis and a matching stream message
    job_id = "job-run-1"
    await fake_redis.hset(
        f"{_JOB_PREFIX}:{job_id}",
        mapping={
            "status": "pending",
            "audio_url": "https://example.com/a.mp3",
            "language": "en",
            "user": "alice",
        },
    )
    await fake_redis.xadd(
        _STREAM,
        {
            "job_id": job_id,
            "audio_url": "https://example.com/a.mp3",
            "language": "en",
            "user": "alice",
            "type": "transcribe",
        },
    )

    processed: list[str] = []

    async def _fast_transcribe(**_kwargs: object) -> dict:  # type: ignore[type-arg]
        processed.append(job_id)
        return _FAST_TRANSCRIPTION

    # When: consumer runs until it processes one message, then is cancelled
    with patch("app.consumer.mock_transcribe", AsyncMock(side_effect=_fast_transcribe)):
        task = asyncio.create_task(
            run_consumer(fake_redis, "consumer-1", mock_qdrant, worker_settings)
        )
        while not processed:
            await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    # Then
    data = await fake_redis.hgetall(f"{_JOB_PREFIX}:{job_id}")
    assert data["status"] == "completed"
