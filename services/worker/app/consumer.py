import asyncio
import json
import logging
import time
from datetime import UTC, datetime

from prometheus_client import Counter, Histogram
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.config import Settings
from app.indexer import index_transcription
from app.mlflow_logger import log_inference_metrics
from app.processors.transcribe import mock_transcribe

_STREAM_KEY = "audiomind:jobs"
_CONSUMER_GROUP = "audiomind:workers"
_JOB_KEY_PREFIX = "audiomind:job"

logger = logging.getLogger(__name__)

# Prometheus metrics
JOBS_PROCESSED_TOTAL = Counter(
    "audiomind_worker_jobs_processed_total",
    "Total number of jobs successfully processed",
)
JOBS_FAILED_TOTAL = Counter(
    "audiomind_worker_jobs_failed_total",
    "Total number of jobs that failed processing",
)
JOB_DURATION_SECONDS = Histogram(
    "audiomind_worker_job_duration_seconds",
    "Duration of job processing in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)


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

    start_time = time.monotonic()
    _elapsed: float = 0.0
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
        JOBS_PROCESSED_TOTAL.inc()
        _elapsed = time.monotonic() - start_time
        tokens_per_second: float | None = None
        token_count = result.get("token_count")
        if isinstance(token_count, (int, float)) and _elapsed > 0:
            tokens_per_second = float(token_count) / _elapsed
        await log_inference_metrics(
            settings,
            job_id=job_id,
            duration_seconds=_elapsed,
            status="completed",
            tokens_per_second=tokens_per_second,
        )
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
        JOBS_FAILED_TOTAL.inc()
        await redis.hset(  # type: ignore[misc]
            job_key,
            mapping={
                "status": "failed",
                "error": str(exc),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )
        await log_inference_metrics(
            settings,
            job_id=job_id,
            duration_seconds=time.monotonic() - start_time,
            status="failed",
            error_type=type(exc).__name__,
        )
    finally:
        JOB_DURATION_SECONDS.observe(_elapsed or (time.monotonic() - start_time))
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
