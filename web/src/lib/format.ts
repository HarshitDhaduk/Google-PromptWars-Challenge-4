/**
 * Small display helpers shared across components, plus client-side mirrors
 * of the service sim clock (service/app/core/clock.py) so the 3D broadcast
 * can animate smoothly between polls.
 */

import type { Match, Phase, Zone } from "./types";

/** MetLife Stadium local time for a UTC ISO timestamp. */
export function formatStadiumTime(isoUtc: string, locale: string): string {
  const date = new Date(isoUtc);
  if (Number.isNaN(date.getTime())) return "--:--";
  return new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "America/New_York",
  }).format(date);
}

/** Replay scripted goal events to a scoreboard, mirroring the service logic. */
export function scoreAt(match: Match, matchMinute: number | null): [number, number] {
  if (matchMinute === null) return [0, 0];
  let home = 0;
  let away = 0;
  for (const event of match.events) {
    if (event.type !== "goal" || event.minute > matchMinute) continue;
    if (event.team === match.home_code) home += 1;
    else if (event.team === match.away_code) away += 1;
  }
  return [home, away];
}

export function walkMinutes(seconds: number): number {
  return Math.max(1, Math.round(seconds / 60));
}

export interface SimAnchor {
  simMs: number;
  realMs: number;
  speed: number;
  kickoffMs: number;
}

/** Anchor the accelerated sim clock to a known (sim time, real time) pair. */
export function makeSimAnchor(
  simTimeIso: string,
  speed: number,
  kickoffUtc: string,
  realNowMs: number,
): SimAnchor {
  return {
    simMs: Date.parse(simTimeIso),
    realMs: realNowMs,
    speed,
    kickoffMs: Date.parse(kickoffUtc),
  };
}

/** Wall-clock minutes relative to kickoff at a given real timestamp. */
export function wallMinuteAt(anchor: SimAnchor, realNowMs: number): number {
  const simNowMs = anchor.simMs + (realNowMs - anchor.realMs) * anchor.speed;
  return (simNowMs - anchor.kickoffMs) / 60_000;
}

export function phaseForWallMinute(minute: number): Phase {
  if (minute < 0) return "pre_match";
  if (minute < 45) return "first_half";
  if (minute < 60) return "halftime";
  if (minute < 105) return "second_half";
  return "post_match";
}

/** Scoreboard minute (0-90, frozen at full time), or null before kickoff. */
export function scoreboardMinute(minute: number): number | null {
  if (minute < 0) return null;
  if (minute < 45) return Math.floor(minute);
  if (minute < 60) return 45;
  return Math.min(Math.floor(minute - 15), 90);
}

/** Compact map label, e.g. "Gate C", "320-326", "E 100", "Rail & Bus". */
export function zoneMapLabel(zone: Zone): string {
  switch (zone.kind) {
    case "gate":
      return zone.name.replace(/\s*\(.*\)$/, "");
    case "section": {
      const match = zone.id.match(/^sec_(\d+)_(\d+)$/);
      return match ? `${match[1]}-${match[2]}` : zone.name;
    }
    case "concourse": {
      const match = zone.id.match(/^conc_(\d+)_([nesw])$/);
      return match ? `${match[2].toUpperCase()} ${match[1]}` : zone.name;
    }
    case "transit":
      return "Rail & Bus";
    default:
      return zone.name;
  }
}
