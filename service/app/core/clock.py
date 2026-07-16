"""Accelerated simulation clock and match-day phase derivation.

All timing is expressed as a single float: wall-clock minutes relative to
kickoff (negative before). Stoppage time is ignored (documented assumption):
first half 0-45, halftime 45-60, second half 60-105, post-match >= 105.
"""

import math
import time
from datetime import datetime, timedelta
from typing import Callable

from ..models.entities import Phase

HALFTIME_START = 45.0
SECOND_HALF_START = 60.0
FULL_TIME = 105.0
HALFTIME_BREAK = SECOND_HALF_START - HALFTIME_START


def phase_for_minute(minute: float) -> Phase:
    if minute < 0:
        return "pre_match"
    if minute < HALFTIME_START:
        return "first_half"
    if minute < SECOND_HALF_START:
        return "halftime"
    if minute < FULL_TIME:
        return "second_half"
    return "post_match"


def match_minute_for(minute: float) -> int | None:
    """Scoreboard minute (0-90, frozen at full time), or None before kickoff."""
    if minute < 0:
        return None
    if minute < HALFTIME_START:
        return int(minute)
    if minute < SECOND_HALF_START:
        return int(HALFTIME_START)
    return min(int(minute - HALFTIME_BREAK), 90)


def minutes_to_kickoff_for(minute: float) -> int | None:
    """Whole minutes until kickoff, or None once the match has started."""
    if minute >= 0:
        return None
    return math.ceil(-minute)


class SimClock:
    """Maps real elapsed time onto an accelerated match-day timeline.

    sim_minute = start_offset + speed * real_minutes_elapsed, with minute 0
    at kickoff. `now_fn` is injectable so tests can freeze or step time.
    """

    def __init__(
        self,
        kickoff_utc: datetime,
        start_offset_min: float,
        speed: float,
        now_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kickoff = kickoff_utc
        self._start_offset_min = start_offset_min
        self._speed = speed
        self._now_fn = now_fn
        self._started_at = now_fn()

    @property
    def speed(self) -> float:
        return self._speed

    def sim_minute(self) -> float:
        real_minutes = (self._now_fn() - self._started_at) / 60.0
        return self._start_offset_min + self._speed * real_minutes

    def sim_time(self) -> datetime:
        return self._kickoff + timedelta(minutes=self.sim_minute())
