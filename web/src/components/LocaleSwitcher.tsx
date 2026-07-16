"use client";

import { useI18n } from "../lib/i18n";
import { LOCALES, type Locale } from "../lib/types";

const LOCALE_LABELS: Record<Locale, string> = {
  en: "English",
  es: "Español",
  fr: "Français",
  ar: "العربية",
  pt: "Português",
  de: "Deutsch",
};

export function LocaleSwitcher() {
  const { locale, setLocale, t } = useI18n();

  return (
    <label className="flex items-center gap-2">
      <span aria-hidden className="text-base">
        🌐
      </span>
      <span className="sr-only">{t("language_label")}</span>
      <select
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
        className="rounded-lg border border-edge bg-panel px-2 py-1.5 text-sm text-ink hover:border-accent/60"
      >
        {LOCALES.map((code) => (
          <option key={code} value={code}>
            {LOCALE_LABELS[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
