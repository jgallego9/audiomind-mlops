import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.config import Settings, get_settings
from app.dependencies.auth import CurrentUser
from app.dependencies.qdrant import QdrantDep
from app.middleware.rate_limit import limiter
from app.models.search import SearchHit, SearchRequest, SearchResponse

router = APIRouter(tags=["search"])
logger = logging.getLogger(__name__)


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search over transcriptions",
)
@limiter.limit("30/minute")
async def search_transcriptions(
    request: Request,
    body: SearchRequest,
    qdrant: QdrantDep,
    current_user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchResponse:
    """Find transcriptions semantically similar to ``body.query``.

    Results are scoped to the authenticated user's own transcriptions.
    """
    query_filter = Filter(
        must=[
            FieldCondition(
                key="user",
                match=MatchValue(value=current_user.subject),
            )
        ]
    )
    try:
        hits = await qdrant.query(
            collection_name=settings.qdrant_collection,
            query_text=body.query,
            query_filter=query_filter,
            limit=body.limit,
        )
    except UnexpectedResponse as exc:
        if exc.status_code == 404:
            # Collection doesn't exist yet — no transcriptions indexed.
            return SearchResponse(results=[], total=0)
        raise

    results = [
        SearchHit(
            job_id=str(hit.id),
            score=round(hit.score, 4),
            transcript=hit.document,
            language=str(hit.metadata.get("language", "")),
            audio_url=str(hit.metadata.get("audio_url", "")),
            created_at=str(hit.metadata.get("created_at", "")),
        )
        for hit in hits
    ]
    return SearchResponse(results=results, total=len(results))
