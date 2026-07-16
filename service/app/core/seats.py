"""Deterministic per-section seat availability simulation.

Availability is a pure function of (seed, section, sim minute): a sales
curve that tightens toward kickoff, a fixed per-section offset, and a few
"hospitality release" sections that keep a small block available. Like the
crowd simulation there is no mutable state, so answers are reproducible
across the API, the chat tools, and tests.
"""

import zlib

from ..models.entities import SeatInfo, SeatStatus, Zone
from .stadium import StadiumRepository

CAPACITY_BY_LEVEL = {100: 620, 300: 480}
DEFAULT_CAPACITY = 500
LIMITED_THRESHOLD = 25

# (minute relative to kickoff, fraction of seats sold), linearly interpolated.
# A World Cup Final: most sections sell out well before kickoff; the seats
# that remain are hospitality returns and official-resale releases.
SALES_CURVE: list[tuple[float, float]] = [
    (-240, 0.970),
    (-120, 0.985),
    (-60, 0.995),
    (-30, 0.998),
    (0, 1.0),
]

_WIGGLE_AMPLITUDE = 0.01
_RELEASE_HOLD = 0.04  # hospitality/resale block kept by every 3rd section
_SOLD_MIN, _SOLD_MAX = 0.90, 1.0


def seat_status(available: int) -> SeatStatus:
    if available <= 0:
        return "sold_out"
    if available <= LIMITED_THRESHOLD:
        return "limited"
    return "available"


def _sold_ratio_curve(minute: float) -> float:
    if minute <= SALES_CURVE[0][0]:
        return SALES_CURVE[0][1]
    if minute >= SALES_CURVE[-1][0]:
        return SALES_CURVE[-1][1]
    for (m0, v0), (m1, v1) in zip(SALES_CURVE, SALES_CURVE[1:]):
        if m0 <= minute <= m1:
            fraction = (minute - m0) / (m1 - m0)
            return v0 + (v1 - v0) * fraction
    raise AssertionError("SALES_CURVE must be sorted by minute")


class SeatSimulator:
    def __init__(self, repo: StadiumRepository, seed: int) -> None:
        self._seed = seed
        self._section_zone: dict[str, Zone] = {
            section: zone
            for zone in repo.zones
            if zone.sections
            for section in zone.sections
        }

    @property
    def sections(self) -> list[str]:
        return sorted(self._section_zone)

    def info(self, section: str, minute: float) -> SeatInfo:
        zone = self._section_zone[section]
        capacity = CAPACITY_BY_LEVEL.get(zone.level, DEFAULT_CAPACITY)

        unit = (zlib.crc32(f"{self._seed}:seat:{section}".encode()) % 1000) / 999.0
        wiggle = (unit * 2.0 - 1.0) * _WIGGLE_AMPLITUDE
        hold = _RELEASE_HOLD if zlib.crc32(section.encode()) % 3 == 0 else 0.0

        sold = _sold_ratio_curve(minute) + wiggle - hold
        sold = min(_SOLD_MAX, max(_SOLD_MIN, sold))
        available = max(0, round(capacity * (1.0 - sold)))

        return SeatInfo(
            section=section,
            zone_id=zone.id,
            level=zone.level,
            capacity=capacity,
            available=available,
            status=seat_status(available),
        )

    def snapshot(self, minute: float) -> dict[str, SeatInfo]:
        return {section: self.info(section, minute) for section in self.sections}
