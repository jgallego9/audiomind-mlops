import logging

from qdrant_client import AsyncQdrantClient

from app.config import Settings

logger = logging.getLogger(__name__)


async def index_transcription(
    qdrant: AsyncQdrantClient,
    settings: Settings,
    *,
    job_id: str,
    transcript: str,
    language: str,
    audio_url: str,
    user: str,
    created_at: str,
) -> None:
    """Index a completed transcription into Qdrant for semantic search.

    :param qdrant: Async Qdrant client.
    :param settings: Worker settings (collection name, embedding model).
    :param job_id: Unique job identifier (used as point ID).
    :param transcript: Full transcription text to embed.
    :param language: Detected or requested language code.
    :param audio_url: Source audio URL stored as metadata.
    :param user: Owner's username — used to scope search results.
    :param created_at: ISO-8601 completion timestamp.
    """
    try:
        await qdrant.add(
            collection_name=settings.qdrant_collection,
            documents=[transcript],
            metadata=[
                {
                    "user": user,
                    "language": language,
                    "audio_url": audio_url,
                    "created_at": created_at,
                }
            ],
            ids=[job_id],
        )
        logger.info(
            "indexed job_id=%s collection=%s", job_id, settings.qdrant_collection
        )
    except Exception:  # noqa: BLE001
        logger.exception("index_failed job_id=%s", job_id)
