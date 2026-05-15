"""Pydantic models for pipeline API routes."""

from typing import Any

from pydantic import BaseModel


class PipelineJobRequest(BaseModel):
    """Request body for ``POST /v1/pipelines/{id}/jobs``.

    :param payload: Arbitrary ``{key: value}`` dict of job inputs.
    """

    payload: dict[str, Any]


class PipelineJobResponse(BaseModel):
    """Response body for ``POST /v1/pipelines/{id}/jobs``.

    :param job_id: UUID of the created job.
    :param pipeline_id: Pipeline that will process the job.
    :param status: Initial status — always ``"pending"``.
    :param created_at: ISO-8601 timestamp of job creation.
    """

    job_id: str
    pipeline_id: str
    status: str
    created_at: str


class StepInfo(BaseModel):
    """Summary of a single step inside a pipeline.

    :param id: Step identifier (equals the KServe V2 model name).
    :param task: Inferflow task schema name.
    :param url: Base URL of the step service.
    """

    id: str
    task: str
    url: str


class PipelineInfo(BaseModel):
    """Public representation of a pipeline as returned by ``GET /v1/pipelines``.

    :param id: Unique pipeline identifier (equals its ``name``).
    :param name: Pipeline name.
    :param version: Semantic version string.
    :param description: Human-readable description.
    :param stream: Redis Stream key where jobs are published.
    :param steps: Ordered list of steps declared in the pipeline.
    """

    id: str
    name: str
    version: str
    description: str
    stream: str
    steps: list[StepInfo]
