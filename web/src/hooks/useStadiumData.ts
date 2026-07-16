"use client";

/**
 * One-shot load of the static stadium graph and fan context, with
 * service-down detection and manual retry.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchContext, fetchStadium } from "../lib/api";
import type { ContextResponse, StadiumResponse, Zone } from "../lib/types";

export type StadiumStatus = "loading" | "ready" | "down";

export interface StadiumData {
  status: StadiumStatus;
  stadium: StadiumResponse | null;
  context: ContextResponse | null;
  zonesById: Map<string, Zone>;
  retry: () => void;
}

export function useStadiumData(): StadiumData {
  const [status, setStatus] = useState<StadiumStatus>("loading");
  const [stadium, setStadium] = useState<StadiumResponse | null>(null);
  const [context, setContext] = useState<ContextResponse | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchStadium(), fetchContext()])
      .then(([stadiumResponse, contextResponse]) => {
        if (cancelled) return;
        setStadium(stadiumResponse);
        setContext(contextResponse);
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("down");
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setStatus("loading");
    setAttempt((current) => current + 1);
  }, []);

  const zonesById = useMemo(() => {
    const map = new Map<string, Zone>();
    for (const zone of stadium?.zones ?? []) map.set(zone.id, zone);
    return map;
  }, [stadium]);

  return { status, stadium, context, zonesById, retry };
}
