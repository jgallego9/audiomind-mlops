import asyncio
import json
import logging
from datetime import datetime, timezone

from redis.asyncio import Redis  # type: ignore[import-untyped]

from app.processors.transcribe import mock_transcribe

_STREAM_KEY = "audiomind:jobs"
_CONSUMER_GROUP = "audiomind:workers"
_JOB_KEY_PREFIX = "audiomind:job"

logger = logging.getLogger(__name__)


async def _ensure_consumer_group(redis: "Redis[str]") -> None:
    """Create the consumer group (and stream) if they do not yet exist."""
    try:
        await redis.xgroup_create(_STREAM_KEY, _CONSUMER_GROUP, id="0", mkstream=True)  # type: ignore[misc]
        logger.info(
            "consumer_group_created group=%s stream=%s", _CONSUMER_GROUP, _STREAM_KEY
        )
    except Exception as exc:  # noqa: BLE001
        if "BUSYGROUP" not in str(exc):
            raise


async def _process_message(
    redis: "Redis[str]",
    msg_id: str,
    fields: dict[str, str],
) -> None:
    job_id: str = fields.get("job_id", "")
    audio_url: str = fields.get("audio_url", "")
    language: str = fields.get("language", "auto")
    job_key = f"{_JOB_KEY_PREFIX}:{job_id}"

    logger.info("job_start job_id=%s audio_url=%s", job_id, audio_url)
    await redis.hset(job_key, "status", "processing")  # type: ignore[misc]

    try:
        result = await mock_transcribe(audio_url=audio_url, language=language)
        await redis.hset(  # type: ignore[misc]
            job_key,
            mapping={
                "status": "completed",
                "result": json.dumps(result),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info("job_done job_id=%s", job_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("job_failed job_id=%s error=%s", job_id, exc)
        await redis.hset(  # type: ignore[misc]
            job_key,
            mapping={
                "status": "failed",
                "error": str(exc),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    finally:
        await redis.xack(_STREAM_KEY, _CONSUMER_GROUP, msg_id)  # type: ignore[misc]


async def run_consumer(redis: "Redis[str]", consumer_id: str) -> None:
    """Blocking consumer loop — reads from the Redis Stream and processes jobs."""
    await _ensure_consumer_group(redis)
    logger.info("consumer_ready consumer=%s", consumer_id)

    while True:
        try:
            results: list[
                tuple[str, list[tuple[str, dict[str, str]]]]
            ] = await redis.xreadgroup(  # type: ignore[misc]
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
                    await _process_message(redis, msg_id, fields)
        except asyncio.CancelledError:
            logger.info("consumer_shutdown consumer=%s", consumer_id)
            break
        except Exception:  # noqa: BLE001
            logger.exception("consumer_error consumer=%s — retrying in 2s", consumer_id)
            await asyncio.sleep(2)
