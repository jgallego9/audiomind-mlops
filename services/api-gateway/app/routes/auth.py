from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status
from jose import jwt  # type: ignore[import-untyped]
from passlib.context import CryptContext  # type: ignore[import-untyped]

from app.config import settings
from app.middleware.rate_limit import limiter
from app.models.auth import LoginRequest, Token

router = APIRouter(tags=["auth"])

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo credentials — in production replace with a database-backed user store.
# Generate hash: python -c "from passlib.context import CryptContext; \
#   print(CryptContext(schemes=['bcrypt']).hash('your-password'))"
_DEMO_USERNAME = "admin"
_DEMO_PASSWORD_HASH = _pwd_context.hash("demo-password")


def _verify_password(plain: str, hashed: str) -> bool:
    result: bool = _pwd_context.verify(plain, hashed)
    return result


def _create_access_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    encoded: str = jwt.encode(
        {"sub": subject, "exp": expire},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return encoded


@router.post("/token", response_model=Token, summary="Issue JWT access token")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest) -> Token:
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
    return Token(access_token=_create_access_token(body.username))
