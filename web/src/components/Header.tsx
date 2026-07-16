"use client";

import { formatStadiumTime, scoreAt } from "../lib/format";
import { useI18n } from "../lib/i18n";
import type { ContextResponse, CrowdResponse } from "../lib/types";
import { LocaleSwitcher } from "./LocaleSwitcher";

function Chip({ children, label }: { children: React.ReactNode; label?: string }) {
  return (
    <span
      aria-label={label}
      className="inline-flex items-center gap-1.5 rounded-full border border-edge bg-panel px-3 py-1 text-xs text-ink-dim"
    >
      {children}
    </span>
  );
}

export function Header({
  context,
  crowd,
}: {
  context: ContextResponse | null;
  crowd: CrowdResponse | null;
}) {
  const { t, locale } = useI18n();

  const phase = crowd?.phase ?? context?.sim.phase ?? null;
  const simTime = crowd?.sim_time ?? context?.sim.sim_time ?? null;
  const matchMinute = crowd?.match_minute ?? context?.sim.match_minute ?? null;
  const minutesToKickoff =
    crowd?.minutes_to_kickoff ?? context?.sim.minutes_to_kickoff ?? null;

  let matchChip: string | null = null;
  if (context) {
    if (minutesToKickoff !== null) {
      matchChip = t("kickoff_in", { minutes: minutesToKickoff });
    } else {
      const [homeGoals, awayGoals] = scoreAt(context.match, matchMinute);
      const clock = matchMinute !== null ? ` · ${matchMinute}'` : "";
      matchChip = `${context.match.home_code} ${homeGoals}-${awayGoals} ${context.match.away_code}${clock}`;
    }
  }

  const isGemini = context?.provider === "gemini";

  return (
    <header className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <div className="me-auto">
        <h1 className="text-xl font-bold tracking-tight">
          {t("app_title")} <span aria-hidden>⚽</span>
        </h1>
        <p className="text-sm text-ink-dim">{t("app_subtitle")} · MetLife Stadium</p>
      </div>

      {matchChip && (
        <Chip>
          <strong className="font-semibold text-ink">{matchChip}</strong>
        </Chip>
      )}
      {phase && <Chip>{t(`phase_${phase}`)}</Chip>}
      {simTime && (
        <Chip label={t("sim_time_label")}>
          <span aria-hidden>🕒</span>
          {formatStadiumTime(simTime, locale)} ET
          {context && (
            <span className="text-ink-dim/70">· {t("sim_speed", { speed: context.sim.speed })}</span>
          )}
        </Chip>
      )}
      {context && (
        <Chip>
          <span
            aria-hidden
            className={`size-2 rounded-full ${isGemini ? "bg-accent-2" : "bg-crowd-moderate"}`}
          />
          {isGemini ? t("provider_gemini") : t("provider_demo")}
        </Chip>
      )}
      <LocaleSwitcher />
    </header>
  );
}
