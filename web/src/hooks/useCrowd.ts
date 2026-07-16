"use client";

/**
 * Polls live crowd state every 15 s; pauses while the tab is hidden and
 * refreshes immediately when it becomes visible again.
 */

import { useEffect, useState } from "react";

import { fetchCrowd } from "../lib/api";
import type { CrowdResponse } from "../lib/types";

const POLL_INTERVAL_MS = 15_000;

export interface CrowdState {
  crowd: CrowdResponse | null;
  failed: boolean;
}

export function useCrowd(enabled: boolean): CrowdState {
  const [crowd, setCrowd] = useState<CrowdResponse | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    let timer: number | undefined;
    let firstFetch = true;

    async function tick() {
      // Always fetch once so the map has data even in background tabs;
      // afterwards, skip polls while hidden.
      if (firstFetch || !document.hidden) {
        firstFetch = false;
        try {
          const snapshot = await fetchCrowd();
          if (!cancelled) {
            setCrowd(snapshot);
            setFailed(false);
          }
        } catch {
          if (!cancelled) setFailed(true);
        }
      }
      if (!cancelled) timer = window.setTimeout(tick, POLL_INTERVAL_MS);
    }

    function onVisibilityChange() {
      if (!document.hidden && !cancelled) {
        window.clearTimeout(timer);
        void tick();
      }
    }

    void tick();
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [enabled]);

  return { crowd, failed };
}
