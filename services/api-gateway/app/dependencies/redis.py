from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis


async def get_redis(request: Request) -> Redis:
    """Return the shared async Redis client stored on app state."""
    return request.app.state.redis  # type: ignore[no-any-return]


RedisClient = Annotated[Redis, Depends(get_redis)]
