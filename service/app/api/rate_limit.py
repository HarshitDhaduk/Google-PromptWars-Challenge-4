"""Sliding-window rate limiting with no external dependencies.

Guards the Gemini free-tier quota and keeps the demo service unabusable:
chat is limited per session and globally; cheap read endpoints share one
generous global bucket.
"""

import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from fastapi import HTTPException, Request

from ..models.api import ChatRequest

CHAT_SESSION_LIMIT_PER_MIN = 10
CHAT_GLOBAL_LIMIT_PER_MIN = 30
READ_GLOBAL_LIMIT_PER_MIN = 240
WINDOW_SECONDS = 60.0
_KEY_PRUNE_THRESHOLD = 1024


class SlidingWindowLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float = WINDOW_SECONDS,
        now_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._now_fn = now_fn
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def try_acquire(self, key: str) -> float | None:
        """None if allowed (and recorded); otherwise seconds until a slot frees."""
        now = self._now_fn()
        cutoff = now - self._window
        with self._lock:
            if len(self._hits) > _KEY_PRUNE_THRESHOLD:
                stale = [k for k, q in self._hits.items() if not q or q[-1] <= cutoff]
                for k in stale:
                    del self._hits[k]
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self._limit:
                return self._window - (now - hits[0])
            hits.append(now)
            return None


@dataclass
class Limiters:
    chat_session: SlidingWindowLimiter = field(
        default_factory=lambda: SlidingWindowLimiter(CHAT_SESSION_LIMIT_PER_MIN)
    )
    chat_global: SlidingWindowLimiter = field(
        default_factory=lambda: SlidingWindowLimiter(CHAT_GLOBAL_LIMIT_PER_MIN)
    )
    reads: SlidingWindowLimiter = field(
        default_factory=lambda: SlidingWindowLimiter(READ_GLOBAL_LIMIT_PER_MIN)
    )


def _reject(retry_after_seconds: float) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={"code": "rate_limited", "message": "Too many requests - please slow down."},
        headers={"Retry-After": str(max(1, math.ceil(retry_after_seconds)))},
    )


def enforce_chat_limits(request: Request, payload: ChatRequest) -> ChatRequest:
    """Body-parsing dependency: validates the payload once and applies both
    chat buckets. Denied requests do not consume quota."""
    limiters: Limiters = request.app.state.limiters
    retry = limiters.chat_global.try_acquire("global")
    if retry is not None:
        raise _reject(retry)
    retry = limiters.chat_session.try_acquire(payload.session_id)
    if retry is not None:
        raise _reject(retry)
    return payload


def enforce_read_limits(request: Request) -> None:
    limiters: Limiters = request.app.state.limiters
    retry = limiters.reads.try_acquire("global")
    if retry is not None:
        raise _reject(retry)
