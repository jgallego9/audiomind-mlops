import asyncio
import json
import logging
from datetime import UTC, datetime

from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.config import Settings
from app.indexer import index_transcription
from app.processors.transcribe import mock_transcribe

_STREAM_KEY = "audiomind:jobs"
_CONSUMER_GROUP = "audiomind:workers"
_JOB_KEY_PREFIX = "audiomind:job"

logger = logging.getLogger(__name__)


async def _ensure_consumer_group(redis: Redis) -> None:
    """Create the consumer group (and stream) if they do not yet exist."""
    try:
        await redis.xgroup_create(_STREAM_KEY, _CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(
            "consumer_group_created group=%s stream=%s", _CONSUMER_GROUP, _STREAM_KEY
        )
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _process_message(
    redis: Redis,
    qdrant: AsyncQdrantClient,
    settings: Settings,
    msg_id: str,
    fields: dict[str, str],
) -> None:
    job_id: str = fields.get("job_id", "")
    audio_url: str = fields.get("audio_url", "")
    language: str = fields.get("language", "auto")
    user: str = fields.get("user", "")
    job_key = f"{_JOB_KEY_PREFIX}:{job_id}"

    logger.info("job_start job_id=%s audio_url=%s", job_id, audio_url)
    await redis.hset(job_key, "status", "processing")  # type: ignore[misc]

    try:
        result = await mock_transcribe(audio_url=audio_url, language=language)
        completed_at = datetime.now(UTC).isoformat()
        await redis.hset(  # type: ignore[misc]
            job_key,
            mapping={
                "status": "completed",
                "result": json.dumps(result),
                "completed_at": completed_at,
            },
        )
        logger.info("job_done job_id=%s", job_id)
        # Index the transcription for semantic search (best-effort).
        transcript = str(result.get("transcript", ""))
        await index_transcription(
            qdrant,
            settings,
            job_id=job_id,
            transcript=transcript,
            language=str(result.get("language", language)),
            audio_url=audio_url,
            user=user,
            created_at=completed_at,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("job_failed job_id=%s error=%s", job_id, exc)
        await redis.hset(  # type: ignore[misc]
            job_key,
            mapping={
                "status": "failed",
                "error": str(exc),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )
    finally:
        await redis.xack(_STREAM_KEY, _CONSUMER_GROUP, msg_id)


async def _recover_pending(
    redis: Redis,
    qdrant: AsyncQdrantClient,
    settings: Settings,
    consumer_id: str,
) -> None:
    """Re-claim messages that have been pending for >60 s (previous worker crash).

    Uses XAUTOCLAIM (Redis >= 6.2) to atomically steal stale PEL entries.
    """
    try:
        _next_id, messages, _deleted = await redis.xautoclaim(
            name=_STREAM_KEY,
            groupname=_CONSUMER_GROUP,
            consumername=consumer_id,
            min_idle_time=60_000,  # ms
            start_id="0-0",
            count=10,
        )
        if messages:
            logger.info(
                "recovered_pending count=%d consumer=%s", len(messages), consumer_id
            )
            for msg_id, fields in messages:
                await _process_message(redis, qdrant, settings, msg_id, fields)
    except Exception:  # noqa: BLE001
        logger.warning(
            "pending_recovery_skipped consumer=%s", consumer_id, exc_info=True
        )


async def run_consumer(
    redis: Redis, consumer_id: str, qdrant: AsyncQdrantClient, settings: Settings
) -> None:
    """Blocking consumer loop — reads from the Redis Stream and processes jobs."""
    await _ensure_consumer_group(redis)
    await _recover_pending(redis, qdrant, settings, consumer_id)  # claim stale msgs
    logger.info("consumer_ready consumer=%s", consumer_id)

    while True:
        try:
            results: list[
                tuple[str, list[tuple[str, dict[str, str]]]]
            ] = await redis.xreadgroup(
                groupname=_CONSUMER_GROUP,
                consumername=consumer_id,
                streams={_STREAM_KEY: ">"},
                count=1,
                block=5000,  # ms — yields control every 5s when idle
            )
            if not results:
                continue
            for _stream, messages in results:
                for msg_id, fields in messages:
                    await _process_message(redis, qdrant, settings, msg_id, fields)
        except asyncio.CancelledError:
            logger.info("consumer_shutdown consumer=%s", consumer_id)
            break
        except Exception:  # noqa: BLE001
            logger.exception("consumer_error consumer=%s — retrying in 2s", consumer_id)
            await asyncio.sleep(2)
