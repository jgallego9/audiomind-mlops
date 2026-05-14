from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=500, description="Natural language search query"
    )
    limit: int = Field(default=5, ge=1, le=20, description="Max results (1-20)")


class SearchHit(BaseModel):
    job_id: str
    score: float
    transcript: str
    language: str
    audio_url: str
    created_at: str


class SearchResponse(BaseModel):
    results: list[SearchHit]
    total: int
