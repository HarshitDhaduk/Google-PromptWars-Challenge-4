"use client";

/**
 * Localized, structured rendering of a route: the service sends structured
 * step fields (edge kind, seconds, congestion), and this card rebuilds the
 * instructions from i18n templates so they follow the UI language.
 */

import { walkMinutes } from "../../lib/format";
import { useI18n, type Translate } from "../../lib/i18n";
import type { RouteResult, RouteStep, Zone } from "../../lib/types";

function localizedInstruction(
  step: RouteStep,
  index: number,
  steps: RouteStep[],
  zonesById: Map<string, Zone>,
  t: Translate,
): string {
  if (step.edge_kind === null) {
    const key = step.zone_id.startsWith("gate_") ? "step_enter" : "step_start";
    return t(key, { name: step.name });
  }
  const minutes = walkMinutes(step.seconds);
  if (step.edge_kind === "walkway") {
    return t("step_walk", {
      name: step.name,
      minutes,
      congestion: t(`crowd_${step.congestion}`),
    });
  }
  const previousLevel = zonesById.get(steps[index - 1]?.zone_id ?? "")?.level ?? 0;
  const currentLevel = zonesById.get(step.zone_id)?.level ?? 0;
  const direction = currentLevel > previousLevel ? "up" : "down";
  return t(`step_${step.edge_kind}_${direction}`, { name: step.name, minutes });
}

export function RouteStepsCard({
  route,
  zonesById,
}: {
  route: RouteResult;
  zonesById: Map<string, Zone>;
}) {
  const { t } = useI18n();

  return (
    <div className="mt-2 rounded-xl border border-edge bg-panel-2 p-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-semibold text-ink">{t("route_title")}</span>
        <span className="text-ink-dim">
          {t("route_total", { minutes: walkMinutes(route.total_seconds) })}
        </span>
        {route.accessible && (
          <span className="rounded-full border border-accent-2/50 bg-accent-2/10 px-2 py-0.5 text-accent-2">
            ♿ {t("route_accessible_badge")}
          </span>
        )}
      </div>
      <ol className="mt-2 space-y-1.5">
        {route.steps.map((step, index) => (
          <li key={`${step.zone_id}-${index}`} className="flex items-start gap-2 text-sm">
            <span
              aria-hidden
              className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-panel text-[10px] font-bold text-ink-dim"
            >
              {index + 1}
            </span>
            <span className="flex-1 text-ink">
              {localizedInstruction(step, index, route.steps, zonesById, t)}
            </span>
            {step.edge_kind !== null && (
              <span
                aria-label={t(`crowd_${step.congestion}`)}
                title={t(`crowd_${step.congestion}`)}
                className="mt-1.5 size-2.5 shrink-0 rounded-full"
                style={{ background: `var(--color-crowd-${step.congestion})` }}
              />
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
