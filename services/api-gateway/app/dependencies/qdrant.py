from typing import Annotated

from fastapi import Depends, Request
from qdrant_client import AsyncQdrantClient


async def get_qdrant(request: Request) -> AsyncQdrantClient:
    return request.app.state.qdrant  # type: ignore[no-any-return]


QdrantDep = Annotated[AsyncQdrantClient, Depends(get_qdrant)]
