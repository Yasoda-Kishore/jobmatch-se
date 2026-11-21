"""A simple per-visitor limit, so a public website can't use up the LLM quota."""
import os
import threading
import time
from collections import defaultdict, deque

MATCHES_PER_HOUR = int(os.getenv("MATCHES_PER_HOUR", "5"))
_history: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def allow(visitor: str, limit: int | None = None, window_s: float = 3600.0) -> bool:
    """True if this visitor may do one more match now. Each visitor gets `limit` per hour."""
    limit = MATCHES_PER_HOUR if limit is None else limit
    now = time.monotonic()
    with _lock:
        times = _history[visitor]
        while times and now - times[0] > window_s:
            times.popleft()  # forget matches older than one hour
        if len(times) >= limit:
            return False
        times.append(now)
        return True
