from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

# Single Limiter instance shared across the application.
# Default limit is driven by Settings.rate_limit_default and overridden
# per-route with @limiter.limit("N/period").
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[get_settings().rate_limit_default],
)
