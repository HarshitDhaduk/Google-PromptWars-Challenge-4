"use client";

import type { ChatMessage } from "../../hooks/useChat";
import { useI18n } from "../../lib/i18n";
import type { Zone } from "../../lib/types";
import { RouteStepsCard } from "./RouteStepsCard";

const ERROR_KEYS = {
  rate: "chat_error_rate",
  service: "chat_error_service",
  generic: "chat_error_generic",
} as const;

export function MessageBubble({
  message,
  zonesById,
}: {
  message: ChatMessage;
  zonesById: Map<string, Zone>;
}) {
  const { t } = useI18n();

  if (message.errorKind) {
    return (
      <div className="me-8 rounded-xl border border-crowd-severe/40 bg-crowd-severe/10 px-3 py-2 text-sm text-ink">
        {t(ERROR_KEYS[message.errorKind])}
      </div>
    );
  }

  if (message.role === "user") {
    return (
      <div className="ms-8 flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-ee-sm bg-accent/15 px-3 py-2">
          <p className="sr-only">{t("you_label")}:</p>
          <p className="whitespace-pre-wrap break-words text-sm text-ink">{message.text}</p>
        </div>
      </div>
    );
  }

  const routeAction = message.uiActions?.find((action) => action.type === "show_route");

  return (
    <div className="me-8">
      <div className="max-w-[95%] rounded-2xl rounded-ss-sm border border-edge bg-panel px-3 py-2">
        <p className="whitespace-pre-wrap break-words text-sm leading-relaxed text-ink">
          {message.text}
        </p>
        {routeAction && <RouteStepsCard route={routeAction.route} zonesById={zonesById} />}
        {(message.toolCalls?.length || message.provider === "mock-fallback") && (
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {message.toolCalls?.map((call, index) => (
              <span
                key={`${call.name}-${index}`}
                className="inline-flex items-center gap-1 rounded-full border border-edge bg-panel-2 px-2 py-0.5 text-[10px] text-ink-dim"
              >
                <span aria-hidden>{call.ok ? "⚙️" : "⚠️"}</span>
                {t("grounded_via")} {call.name}
              </span>
            ))}
            {message.provider === "mock-fallback" && (
              <span className="inline-flex items-center gap-1 rounded-full border border-crowd-moderate/40 bg-crowd-moderate/10 px-2 py-0.5 text-[10px] text-crowd-moderate">
                {t("provider_demo")}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
