"use client";

import { useI18n } from "../lib/i18n";

export function ServiceDownBanner({ onRetry }: { onRetry: () => void }) {
  const { t } = useI18n();

  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-xl border border-crowd-moderate/40 bg-crowd-moderate/10 p-4"
    >
      <div className="me-auto">
        <p className="font-semibold text-crowd-moderate">{t("service_down_title")}</p>
        <p className="text-sm text-ink-dim">{t("service_down_body")}</p>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-lg border border-crowd-moderate/50 px-3 py-1.5 text-sm hover:bg-crowd-moderate/20"
      >
        {t("retry")}
      </button>
    </div>
  );
}
