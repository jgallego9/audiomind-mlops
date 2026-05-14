from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.middleware.rate_limit import limiter
from app.models.auth import LoginRequest, Token

router = APIRouter(tags=["auth"])

# Demo credentials — in production replace with a database-backed user store.
# Pre-hash at import time so the first request isn't slow.
_DEMO_USERNAME = "admin"
_DEMO_PASSWORD_HASH: bytes = bcrypt.hashpw(b"demo-password", bcrypt.gensalt())


def _verify_password(plain: str, hashed: bytes) -> bool:
    return bool(bcrypt.checkpw(plain.encode(), hashed))


def _create_access_token(subject: str, settings: Settings) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


@router.post("/token", response_model=Token, summary="Issue JWT access token")
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Token:
    """Authenticate and return a signed JWT.

    Rate-limited to 10 requests/minute per IP to mitigate brute-force attacks.
    """
    if body.username != _DEMO_USERNAME or not _verify_password(
        body.password, _DEMO_PASSWORD_HASH
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=_create_access_token(body.username, settings))
