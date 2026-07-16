"""Deterministic crowd-level simulation.

The crowd level of a zone is a pure function of (zone, sim minute, seed):
a keyframe curve for the zone's kind, a fixed per-zone offset, and smoothed
seeded noise. No mutable state and no background tasks - every caller gets
the same answer for the same sim minute, which keeps routing and tests stable.
"""

import math
import random
import zlib

from ..models.entities import CrowdInfo, CrowdLabel, ZoneKind
from .stadium import StadiumRepository

LEVEL_MIN = 0.05
LEVEL_MAX = 0.97
NOISE_BUCKET_MINUTES = 5.0
NOISE_AMPLITUDE = 0.08
ZONE_OFFSET_AMPLITUDE = 0.05

# (wall minute relative to kickoff, crowd level) keyframes per zone kind,
# linearly interpolated and clamped outside the covered range. They encode
# the match-day story: gate rush before kickoff, concourse spikes at halftime,
# transit crush after the final whistle.
KEYFRAMES: dict[ZoneKind, list[tuple[float, float]]] = {
    "gate": [
        (-180, 0.15), (-90, 0.50), (-30, 0.85), (0, 0.55), (20, 0.25),
        (45, 0.30), (60, 0.30), (90, 0.35), (105, 0.75), (120, 0.80),
        (150, 0.40), (180, 0.20),
    ],
    "concourse": [
        (-180, 0.10), (-60, 0.45), (-15, 0.70), (0, 0.50), (30, 0.30),
        (45, 0.75), (52, 0.80), (60, 0.45), (90, 0.35), (105, 0.70),
        (125, 0.65), (150, 0.35), (180, 0.15),
    ],
    "section": [
        (-180, 0.05), (-45, 0.30), (-10, 0.60), (0, 0.70), (45, 0.50),
        (52, 0.55), (60, 0.65), (100, 0.70), (105, 0.85), (115, 0.60),
        (135, 0.30), (180, 0.10),
    ],
    "transit": [
        (-180, 0.30), (-60, 0.55), (-20, 0.40), (0, 0.15), (60, 0.10),
        (95, 0.30), (105, 0.90), (120, 0.95), (160, 0.60), (180, 0.35),
    ],
}


def crowd_label(level: float) -> CrowdLabel:
    if level < 0.35:
        return "low"
    if level < 0.65:
        return "moderate"
    if level < 0.85:
        return "high"
    return "severe"


def congestion_multiplier(level: float) -> float:
    """Walk-time multiplier: ~1.1x when quiet, up to ~3x in a severe crush."""
    return 1.0 + 2.0 * level


def _interpolate(keyframes: list[tuple[float, float]], minute: float) -> float:
    if minute <= keyframes[0][0]:
        return keyframes[0][1]
    if minute >= keyframes[-1][0]:
        return keyframes[-1][1]
    for (m0, v0), (m1, v1) in zip(keyframes, keyframes[1:]):
        if m0 <= minute <= m1:
            fraction = (minute - m0) / (m1 - m0)
            return v0 + (v1 - v0) * fraction
    raise AssertionError("keyframes must be sorted by minute")


class CrowdSimulator:
    def __init__(self, repo: StadiumRepository, seed: int) -> None:
        self._repo = repo
        self._seed = seed
        # Fixed per-zone "personality" so equal-kind zones do not move in
        # lockstep. crc32 (not built-in hash) keeps it stable across runs.
        self._zone_offset = {zone.id: _hash_offset(zone.id) for zone in repo.zones}

    def level(self, zone_id: str, minute: float) -> float:
        zone = self._repo.zones_by_id[zone_id]
        base = _interpolate(KEYFRAMES[zone.kind], minute)
        raw = base + self._zone_offset[zone_id] + self._noise(zone_id, minute)
        return min(LEVEL_MAX, max(LEVEL_MIN, raw))

    def info(self, zone_id: str, minute: float) -> CrowdInfo:
        level = self.level(zone_id, minute)
        return CrowdInfo(
            level=round(level, 3),
            label=crowd_label(level),
            multiplier=round(congestion_multiplier(level), 2),
        )

    def snapshot(self, minute: float) -> dict[str, CrowdInfo]:
        return {zone.id: self.info(zone.id, minute) for zone in self._repo.zones}

    def _noise(self, zone_id: str, minute: float) -> float:
        """Seeded noise, linearly smoothed between 5-minute buckets."""
        position = minute / NOISE_BUCKET_MINUTES
        bucket = math.floor(position)
        fraction = position - bucket
        n0 = self._bucket_noise(zone_id, bucket)
        n1 = self._bucket_noise(zone_id, bucket + 1)
        smoothed = n0 + (n1 - n0) * fraction
        return (smoothed * 2.0 - 1.0) * NOISE_AMPLITUDE

    def _bucket_noise(self, zone_id: str, bucket: int) -> float:
        return random.Random(f"{self._seed}:{zone_id}:{bucket}").random()


def _hash_offset(zone_id: str) -> float:
    unit = (zlib.crc32(zone_id.encode("utf-8")) % 1000) / 999.0
    return (unit * 2.0 - 1.0) * ZONE_OFFSET_AMPLITUDE
