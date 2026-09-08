from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


# SlowAPI uses the limits storage backend configured here. Development keeps
# an in-process store; production is required to use a shared backend such as
# Redis so limits remain consistent across workers and application instances.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
    storage_uri=settings.rate_limit_storage_uri,
    headers_enabled=True,
)
