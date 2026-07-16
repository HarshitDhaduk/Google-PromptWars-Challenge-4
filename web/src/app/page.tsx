"use client";

/**
 * Composition root: lifts chat ui_actions into map overlay state and wires
 * the live crowd/seat polls, fan context, 2D/3D stadium views, and the chat
 * panel together.
 */

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";

import { Header } from "../components/Header";
import { ServiceDownBanner } from "../components/ServiceDownBanner";
import { TicketCard } from "../components/TicketCard";
import { ChatPanel } from "../components/chat/ChatPanel";
import { CrowdLegend } from "../components/map/CrowdLegend";
import { StadiumMap } from "../components/map/StadiumMap";
import { useChat } from "../hooks/useChat";
import { useCrowd } from "../hooks/useCrowd";
import { useSeats } from "../hooks/useSeats";
import { useStadiumData } from "../hooks/useStadiumData";
import { useI18n } from "../lib/i18n";
import { deriveOverlay, type UiAction } from "../lib/uiActions";

// three.js only loads when the 3D tab is first opened.
const Stadium3D = dynamic(() => import("../components/map/stadium3d/Stadium3D"), {
  ssr: false,
  loading: () => <Loading3D />,
});

function Loading3D() {
  const { t } = useI18n();
  return (
    <div role="status" className="grid h-[420px] place-items-center text-ink-dim md:h-[500px]">
      {t("loading_3d")}
    </div>
  );
}

type MapView = "2d" | "3d";

export default function HomePage() {
  const { t, locale } = useI18n();
  const { status, stadium, context, zonesById, retry } = useStadiumData();
  const { crowd, failed: crowdFailed } = useCrowd(status === "ready");
  const seats = useSeats(status === "ready");
  const [view, setView] = useState<MapView>("2d");
  const [actions, setActions] = useState<UiAction[]>([]);
  const chat = useChat(locale, setActions);

  const overlay = useMemo(() => deriveOverlay(actions), [actions]);
  const serviceDown = status === "down" || crowdFailed;

  function askRouteToSection(section: string) {
    void chat.send(t("route_here_message", { section }));
    setView("2d"); // the route overlay renders on the 2D map
  }

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 p-4 md:p-6">
      <Header context={context} crowd={crowd} />

      {serviceDown && <ServiceDownBanner onRetry={retry} />}
      {status === "loading" && (
        <p role="status" className="py-16 text-center text-ink-dim">
          {t("loading")}
        </p>
      )}

      {status === "ready" && stadium && context && (
        <main className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_400px]">
          <section
            aria-label={t("map_title")}
            className="flex flex-col gap-3 rounded-2xl border border-edge bg-panel p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">{t("map_title")}</h2>
              <div className="flex items-center gap-2">
                {view === "2d" && actions.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setActions([])}
                    className="rounded-lg border border-edge px-2.5 py-1 text-xs text-ink-dim hover:border-accent/60 hover:text-ink"
                  >
                    {t("clear_map")}
                  </button>
                )}
                <div role="group" aria-label={t("map_title")} className="flex rounded-lg border border-edge p-0.5">
                  {(["2d", "3d"] as const).map((option) => (
                    <button
                      key={option}
                      type="button"
                      aria-pressed={view === option}
                      onClick={() => setView(option)}
                      className={`rounded-md px-2.5 py-1 text-xs font-medium ${
                        view === option ? "bg-panel-2 text-ink" : "text-ink-dim hover:text-ink"
                      }`}
                    >
                      {t(`view_${option}`)}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {view === "2d" ? (
              <>
                <StadiumMap stadium={stadium} crowd={crowd} overlay={overlay} />
                <CrowdLegend />
              </>
            ) : (
              <>
                <Stadium3D
                  stadium={stadium}
                  crowd={crowd}
                  seats={seats}
                  context={context}
                  onAskRoute={askRouteToSection}
                />
                <CrowdLegend />
              </>
            )}
          </section>

          <div className="flex min-h-0 flex-col gap-4">
            <TicketCard context={context} />
            <div className="flex min-h-[420px] flex-1 flex-col lg:min-h-0">
              <ChatPanel chat={chat} zonesById={zonesById} />
            </div>
          </div>
        </main>
      )}
    </div>
  );
}
