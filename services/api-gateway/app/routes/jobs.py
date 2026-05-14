import json
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from app.dependencies.auth import CurrentUser
from app.dependencies.redis import RedisClient
from app.middleware.rate_limit import limiter
from app.models.jobs import JobStatus, TranscribeRequest, TranscribeResponse

_STREAM_KEY = "audiomind:jobs"
_JOB_KEY_PREFIX = "audiomind:job"

router = APIRouter(tags=["jobs"])


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit audio for async transcription",
)
@limiter.limit("20/minute")
async def transcribe(
    request: Request,
    body: TranscribeRequest,
    redis: RedisClient,
    current_user: CurrentUser,
) -> TranscribeResponse:
    """Publish a transcription job to the Redis Stream and return the job ID.

    Poll ``GET /jobs/{job_id}`` for status and result.
    """
    job_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    job_key = f"{_JOB_KEY_PREFIX}:{job_id}"

    # Store initial metadata so the status endpoint is queryable immediately.
    await redis.hset(  # type: ignore[misc]
        job_key,
        mapping={
            "status": "pending",
            "audio_url": str(body.audio_url),
            "language": body.language,
            "user": current_user.subject,
            "created_at": created_at,
        },
    )
    await redis.expire(job_key, 3600)  # type: ignore[misc]

    # Publish to the stream for the worker to consume.
    await redis.xadd(  # type: ignore[misc]
        _STREAM_KEY,
        {
            "job_id": job_id,
            "type": "transcribe",
            "audio_url": str(body.audio_url),
            "language": body.language,
            "user": current_user.subject,
        },
    )

    return TranscribeResponse(job_id=job_id, status="pending", created_at=created_at)


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatus,
    summary="Poll transcription job status",
)
async def get_job_status(
    job_id: str,
    redis: RedisClient,
    current_user: CurrentUser,
) -> JobStatus:
    """Return the current status and (when done) result of a transcription job."""
    job_key = f"{_JOB_KEY_PREFIX}:{job_id}"
    data: dict[str, str] = await redis.hgetall(job_key)  # type: ignore[misc]

    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if data.get("user") != current_user.subject:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    result: dict[str, object] | None = None
    if raw := data.get("result"):
        result = json.loads(raw)

    return JobStatus(
        job_id=job_id,
        status=data["status"],  # type: ignore[arg-type]
        audio_url=data.get("audio_url"),
        language=data.get("language"),
        result=result,
        error=data.get("error"),
        created_at=data["created_at"],
        completed_at=data.get("completed_at"),
    )
