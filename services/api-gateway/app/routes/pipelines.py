"""Pipeline API routes — list pipelines and submit jobs.

Routes:
    GET  /v1/pipelines                       — list declared pipelines
    POST /v1/pipelines/{pipeline_id}/jobs    — submit a job to a pipeline
"""

import json
import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from inferflow_shared.pipeline import load_pipelines
from inferflow_shared.schemas import PipelineJobMessage

from app.config import Settings, get_settings
from app.dependencies.auth import CurrentUser
from app.dependencies.redis import RedisClient
from app.middleware.rate_limit import limiter
from app.models.pipelines import (
    PipelineInfo,
    PipelineJobRequest,
    PipelineJobResponse,
    StepInfo,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])

_PIPELINE_JOB_KEY_PREFIX = "pipeline:job"


@router.get("", response_model=list[PipelineInfo], summary="List available pipelines")
async def list_pipelines(
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[PipelineInfo]:
    """Return all pipelines loaded from the ``pipelines/`` directory.

    :param settings: App settings (provides ``pipelines_dir``).
    :returns: List of pipeline summaries; returns an empty list on load errors.
    """
    try:
        pipelines = load_pipelines(settings.pipelines_dir)
    except Exception:  # noqa: BLE001
        logger.exception("pipeline_load_error dir=%s", settings.pipelines_dir)
        return []

    return [
        PipelineInfo(
            id=p.name,
            name=p.name,
            version=p.version,
            description=p.description,
            stream=p.trigger.stream,
            steps=[StepInfo(id=s.id, task=s.task, url=s.url) for s in p.steps],
        )
        for p in pipelines
    ]


@router.post(
    "/{pipeline_id}/jobs",
    response_model=PipelineJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a job to a pipeline",
)
@limiter.limit("20/minute")
async def submit_pipeline_job(
    request: Request,
    pipeline_id: str,
    body: PipelineJobRequest,
    redis: RedisClient,
    current_user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PipelineJobResponse:
    """Accept a pipeline job, publish it to the pipeline's Redis Stream, and
    store a ``pending`` status Hash.

    :param request: Raw FastAPI request (required by slowapi rate limiter).
    :param pipeline_id: Pipeline to target — must match a declared pipeline name.
    :param body: Request body with the job payload.
    :param redis: Async Redis client.
    :param current_user: Authenticated user extracted from the JWT.
    :param settings: App settings.
    :returns: 202 response with job ID and initial status.
    :raises HTTPException 404: When *pipeline_id* is not a known pipeline.
    :raises HTTPException 500: When pipelines cannot be loaded.
    """
    try:
        pipelines = load_pipelines(settings.pipelines_dir)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"Failed to load pipelines: {exc}"
        ) from exc

    pipeline = next((p for p in pipelines if p.name == pipeline_id), None)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline {pipeline_id!r} not found"
        )

    job_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()
    job_key = f"{_PIPELINE_JOB_KEY_PREFIX}:{job_id}"

    await redis.hset(  # type: ignore[misc]
        job_key,
        mapping={
            "status": "pending",
            "pipeline_id": pipeline_id,
            "user": current_user.subject,
            "created_at": created_at,
        },
    )
    await redis.expire(job_key, settings.job_ttl_seconds)

    msg = PipelineJobMessage(
        job_id=job_id,
        pipeline_id=pipeline_id,
        payload=json.dumps(body.payload),
        user=current_user.subject,
    )
    await redis.xadd(
        pipeline.trigger.stream,
        {
            "job_id": msg.job_id,
            "pipeline_id": msg.pipeline_id,
            "payload": msg.payload,
            "user": msg.user,
        },
    )
    logger.info(
        "pipeline_job_submitted job_id=%s pipeline=%s user=%s",
        job_id,
        pipeline_id,
        current_user.subject,
    )
    return PipelineJobResponse(
        job_id=job_id,
        pipeline_id=pipeline_id,
        status="pending",
        created_at=created_at,
    )
