from slowapi import Limiter
from slowapi.util import get_remote_address

# Single Limiter instance shared across the application.
# Default limit is configured via Settings.rate_limit_default and overridden
# per-route with @limiter.limit("N/period").
limiter = Limiter(key_func=get_remote_address)
