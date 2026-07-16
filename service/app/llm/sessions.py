"""In-memory chat history: bounded per session, TTL-evicted, thread-safe."""

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Literal

from .provider import HistoryTurn

MAX_TURNS_PER_SESSION = 20
SESSION_TTL_SECONDS = 30 * 60
MAX_SESSIONS = 500


@dataclass
class _Entry:
    turns: deque[HistoryTurn]
    last_seen: float


class SessionStore:
    def __init__(
        self,
        max_turns: int = MAX_TURNS_PER_SESSION,
        ttl_seconds: float = SESSION_TTL_SECONDS,
        max_sessions: int = MAX_SESSIONS,
        now_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_turns = max_turns
        self._ttl_seconds = ttl_seconds
        self._max_sessions = max_sessions
        self._now_fn = now_fn
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def history(self, session_id: str) -> list[HistoryTurn]:
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                return []
            entry.last_seen = self._now_fn()
            return list(entry.turns)

    def append(self, session_id: str, role: Literal["user", "assistant"], text: str) -> None:
        with self._lock:
            self._evict_locked()
            entry = self._entries.get(session_id)
            if entry is None:
                entry = _Entry(turns=deque(maxlen=self._max_turns), last_seen=0.0)
                self._entries[session_id] = entry
            entry.turns.append(HistoryTurn(role=role, text=text))
            entry.last_seen = self._now_fn()

    def turn_count(self, session_id: str) -> int:
        with self._lock:
            entry = self._entries.get(session_id)
            return len(entry.turns) if entry else 0

    def _evict_locked(self) -> None:
        now = self._now_fn()
        expired = [
            session_id
            for session_id, entry in self._entries.items()
            if now - entry.last_seen > self._ttl_seconds
        ]
        for session_id in expired:
            del self._entries[session_id]
        while len(self._entries) >= self._max_sessions:
            oldest = min(self._entries, key=lambda sid: self._entries[sid].last_seen)
            del self._entries[oldest]
