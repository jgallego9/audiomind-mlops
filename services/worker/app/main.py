"""AudioMind async inference worker.

Consumes transcription jobs from the ``audiomind:jobs`` Redis Stream,
processes them (mock ASR for now), and stores results in Redis Hashes.

Usage:
    python -m app.main
"""

import asyncio
import logging
import signal
import uuid

from prometheus_client import start_http_server
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis

from app.config import get_settings
from app.consumer import run_consumer

_METRICS_PORT = 9090

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def _main() -> None:
    settings = get_settings()
    consumer_id = f"worker-{uuid.uuid4().hex[:8]}"

    logger.info(
        "worker_start consumer=%s redis=%s metrics_port=%d",
        consumer_id,
        settings.redis_url,
        _METRICS_PORT,
    )

    # Expose Prometheus metrics for scraping by PodMonitor
    start_http_server(_METRICS_PORT)

    redis: Redis = Redis.from_url(str(settings.redis_url), decode_responses=True)
    qdrant = AsyncQdrantClient(url=str(settings.qdrant_url))
    qdrant.set_model(settings.embedding_model)

    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("signal_received — initiating graceful shutdown")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    consumer_task = asyncio.create_task(
        run_consumer(redis, consumer_id, qdrant, settings)
    )

    # Block until a SIGINT/SIGTERM arrives.
    await shutdown_event.wait()

    consumer_task.cancel()
    await asyncio.gather(consumer_task, return_exceptions=True)
    await redis.aclose()
    await qdrant.close()

    logger.info("worker_stopped consumer=%s", consumer_id)


if __name__ == "__main__":
    asyncio.run(_main())
