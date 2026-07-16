"use client";

/**
 * Hand-rolled i18n: six locale dictionaries, {var} interpolation, RTL support.
 * Deliberately tiny - a full i18n framework would be over-engineering for
 * ~50 UI strings.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import ar from "../messages/ar.json";
import de from "../messages/de.json";
import en from "../messages/en.json";
import es from "../messages/es.json";
import fr from "../messages/fr.json";
import pt from "../messages/pt.json";
import { LOCALES, type Locale } from "./types";

const MESSAGES: Record<Locale, Record<string, string>> = { en, es, fr, ar, pt, de };

export const RTL_LOCALES: ReadonlySet<Locale> = new Set<Locale>(["ar"]);

const STORAGE_KEY = "stadium-copilot-locale";

export type Translate = (key: string, vars?: Record<string, string | number>) => string;

interface LocaleContextValue {
  locale: Locale;
  dir: "ltr" | "rtl";
  setLocale: (locale: Locale) => void;
  t: Translate;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function translate(
  locale: Locale,
  key: string,
  vars?: Record<string, string | number>,
): string {
  const template = MESSAGES[locale][key] ?? MESSAGES.en[key] ?? key;
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in vars ? String(vars[name]) : match,
  );
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>("en");

  // Restore the saved locale only after mount: the server always renders
  // "en", so reading localStorage during render would cause a hydration
  // mismatch. A one-time post-hydration setState is the intended pattern.
  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- see comment above
    if (isLocale(saved)) setLocale(saved);
  }, []);

  useEffect(() => {
    const dir = RTL_LOCALES.has(locale) ? "rtl" : "ltr";
    document.documentElement.lang = locale;
    document.documentElement.dir = dir;
    window.localStorage.setItem(STORAGE_KEY, locale);
  }, [locale]);

  const t = useCallback<Translate>(
    (key, vars) => translate(locale, key, vars),
    [locale],
  );

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      dir: RTL_LOCALES.has(locale) ? "rtl" : "ltr",
      setLocale,
      t,
    }),
    [locale, t],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useI18n(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (context === null) {
    throw new Error("useI18n must be used inside <LocaleProvider>");
  }
  return context;
}
