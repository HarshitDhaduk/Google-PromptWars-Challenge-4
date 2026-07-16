"use client";

/**
 * Polls seat availability every 30 s; pauses while the tab is hidden.
 * Availability only tightens as kickoff approaches, so a slower cadence
 * than the crowd poll is plenty.
 */

import { useEffect, useState } from "react";

import { fetchSeats } from "../lib/api";
import type { SeatsResponse } from "../lib/types";

const POLL_INTERVAL_MS = 30_000;

export function useSeats(enabled: boolean): SeatsResponse | null {
  const [seats, setSeats] = useState<SeatsResponse | null>(null);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    let timer: number | undefined;
    let firstFetch = true;

    async function tick() {
      if (firstFetch || !document.hidden) {
        firstFetch = false;
        try {
          const snapshot = await fetchSeats();
          if (!cancelled) setSeats(snapshot);
        } catch {
          // The service-down banner is driven by the crowd poll; stay quiet here.
        }
      }
      if (!cancelled) timer = window.setTimeout(tick, POLL_INTERVAL_MS);
    }

    void tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [enabled]);

  return seats;
}
