"use client";

import { useI18n } from "../../lib/i18n";
import type { CrowdLabel } from "../../lib/types";

const LEVELS: readonly CrowdLabel[] = ["low", "moderate", "high", "severe"];

export function CrowdLegend() {
  const { t } = useI18n();

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-dim">
      <span className="font-medium">{t("legend_title")}:</span>
      {LEVELS.map((level) => (
        <span key={level} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="size-2.5 rounded-full"
            style={{ background: `var(--color-crowd-${level})` }}
          />
          {t(`crowd_${level}`)}
        </span>
      ))}
    </div>
  );
}
