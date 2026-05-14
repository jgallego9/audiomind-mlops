import asyncio
import random


async def mock_transcribe(audio_url: str, language: str) -> dict[str, object]:
    """Mock ASR processor — simulates Whisper latency.

    In production, replace this with an HTTP call to the Whisper ASR service.
    """
    # Simulate variable processing time (1–4 seconds)
    await asyncio.sleep(random.uniform(1.0, 4.0))

    detected_language = (
        language if language != "auto" else random.choice(["en", "es", "fr"])
    )

    return {
        "transcript": (
            f"[mock transcript] Audio from {audio_url} processed successfully. "
            "Replace with a real Whisper ASR call in production."
        ),
        "language": detected_language,
        "duration": round(random.uniform(5.0, 120.0), 1),
        "confidence": round(random.uniform(0.85, 0.99), 3),
        "segments": [
            {"start": 0.0, "end": 5.0, "text": "[mock segment 1]"},
        ],
    }
