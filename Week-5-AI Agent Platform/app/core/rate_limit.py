"""Basic in-process rate limiting (per-IP) using slowapi/limits.
Sufficient for a single-instance student deployment; for multi-instance
production, swap the storage backend to Redis (slowapi supports this
via storage_uri= without changing call sites)."""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiting is disabled under pytest (TESTING=1) so the many rapid
# register/login calls made across the test suite -- from the same
# TestClient "IP" -- don't trip limits meant for real abusive traffic.
_TESTING = os.environ.get("TESTING") == "1"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    enabled=not _TESTING,
)
