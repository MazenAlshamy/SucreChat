import time
from collections import defaultdict, deque
from threading import Lock

from app.config import get_settings
from app.errors import too_many

_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return

    now = time.monotonic()
    with _lock:
        bucket = _buckets[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise too_many()
        bucket.append(now)


def reset_rate_limits() -> None:
    with _lock:
        _buckets.clear()
