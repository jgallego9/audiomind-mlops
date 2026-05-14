"""Tests for app.indexer.index_transcription."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.indexer import index_transcription


async def test_index_transcription_calls_qdrant_add(
    mock_qdrant: MagicMock, worker_settings: Settings
) -> None:
    await index_transcription(
        mock_qdrant,
        worker_settings,
        job_id="job-abc",
        transcript="hello world",
        language="en",
        audio_url="https://example.com/audio.mp3",
        user="alice",
        created_at="2026-01-01T00:00:00+00:00",
    )
    mock_qdrant.add.assert_awaited_once()
    call_kwargs = mock_qdrant.add.call_args.kwargs
    assert call_kwargs["collection_name"] == worker_settings.qdrant_collection
    assert call_kwargs["documents"] == ["hello world"]
    assert call_kwargs["ids"] == ["job-abc"]
    metadata = call_kwargs["metadata"][0]
    assert metadata["user"] == "alice"
    assert metadata["language"] == "en"


async def test_index_transcription_swallows_exception(
    mock_qdrant: MagicMock, worker_settings: Settings
) -> None:
    """Index failure must never propagate (best-effort semantic indexing)."""
    mock_qdrant.add = AsyncMock(side_effect=RuntimeError("qdrant-down"))
    # Should not raise.
    await index_transcription(
        mock_qdrant,
        worker_settings,
        job_id="job-err",
        transcript="some text",
        language="en",
        audio_url="https://example.com/audio.mp3",
        user="alice",
        created_at="2026-01-01T00:00:00+00:00",
    )
    mock_qdrant.add.assert_awaited_once()


async def test_index_transcription_logs_exception(
    mock_qdrant: MagicMock, worker_settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    mock_qdrant.add = AsyncMock(side_effect=RuntimeError("timeout"))
    import logging

    with caplog.at_level(logging.ERROR, logger="app.indexer"):
        await index_transcription(
            mock_qdrant,
            worker_settings,
            job_id="job-log",
            transcript="text",
            language="fr",
            audio_url="https://example.com/audio.mp3",
            user="bob",
            created_at="2026-01-01T00:00:00+00:00",
        )
    assert "index_failed" in caplog.text
    assert "job-log" in caplog.text
