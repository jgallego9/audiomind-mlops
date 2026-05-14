from typing import Literal

from pydantic import AnyHttpUrl, BaseModel


class TranscribeRequest(BaseModel):
    audio_url: AnyHttpUrl
    language: str = "auto"


class TranscribeResponse(BaseModel):
    job_id: str
    status: Literal["pending"] = "pending"
    created_at: str


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    audio_url: str | None = None
    language: str | None = None
    result: dict[str, object] | None = None
    error: str | None = None
    created_at: str
    completed_at: str | None = None
