"""Measure every API request: how long it took, and how much LLM work it needed.

Each request gets its own small stats dictionary. The LLM code adds to it,
and when the request is done we log one JSON line and keep it in memory for /metrics.
"""
import json
import logging
import math
import statistics
import threading
from collections import deque
from contextvars import ContextVar

logger = logging.getLogger("jobmatch.requests")
_current: ContextVar[dict | None] = ContextVar("request_stats", default=None)
RECENT: deque[dict] = deque(maxlen=500)  # the last 500 requests
_lock = threading.Lock()  # LLM calls can run in parallel threads


def start_request() -> dict:
    """Create the stats for a new request."""
    stats = {"llm_calls": 0, "llm_tokens_in": 0, "llm_tokens_out": 0, "llm_ms": 0.0}
    _current.set(stats)
    return stats


def record_llm_call(tokens_in: int, tokens_out: int, ms: float) -> None:
    """Called by the LLM code after every call. Does nothing outside a request."""
    stats = _current.get()
    if stats is None:
        return
    with _lock:
        stats["llm_calls"] += 1
        stats["llm_tokens_in"] += tokens_in
        stats["llm_tokens_out"] += tokens_out
        stats["llm_ms"] += ms


def finish_request(stats: dict, method: str, path: str, status: int, duration_ms: float) -> dict:
    """Log one JSON line for the request and remember it."""
    entry = {"method": method, "path": path, "status": status, "duration_ms": round(duration_ms),
             **{k: round(v) if isinstance(v, float) else v for k, v in stats.items()}}
    RECENT.append(entry)
    logger.info(json.dumps(entry))
    return entry


def percentile(values: list[float], share: float) -> float:
    """The value below which `share` of the values fall (0.95 = p95)."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


def summary() -> dict:
    """Per endpoint: number of requests, median and p95 time, and average LLM tokens."""
    result = {}
    for path in sorted({e["path"] for e in RECENT}):
        entries = [e for e in RECENT if e["path"] == path]
        times = [e["duration_ms"] for e in entries]
        result[path] = {
            "requests": len(entries),
            "median_ms": round(statistics.median(times)),
            "p95_ms": round(percentile(times, 0.95)),
            "avg_llm_calls": round(statistics.mean(e["llm_calls"] for e in entries), 1),
            "avg_llm_tokens": round(statistics.mean(e["llm_tokens_in"] + e["llm_tokens_out"] for e in entries)),
        }
    return result
