"use client";

import { useEffect, useRef, useState } from "react";

import type { ChatState } from "../../hooks/useChat";
import { useI18n } from "../../lib/i18n";
import type { Zone } from "../../lib/types";
import { MessageBubble } from "./MessageBubble";
import { QuickActions } from "./QuickActions";

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function ChatPanel({
  chat,
  zonesById,
}: {
  chat: ChatState;
  zonesById: Map<string, Zone>;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({
      behavior: prefersReducedMotion() ? "auto" : "smooth",
      block: "end",
    });
  }, [chat.messages.length, chat.isSending]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    void chat.send(draft);
    setDraft("");
  }

  return (
    <section
      aria-label={t("chat_title")}
      className="flex min-h-0 flex-1 flex-col rounded-2xl border border-edge bg-panel"
    >
      <h2 className="border-b border-edge px-4 py-3 text-sm font-semibold">
        {t("chat_title")}
      </h2>

      <div
        role="log"
        aria-label={t("chat_log_label")}
        aria-live="polite"
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4"
      >
        <div className="me-8 max-w-[95%] rounded-2xl rounded-ss-sm border border-edge bg-panel-2 px-3 py-2">
          <p className="text-sm leading-relaxed text-ink">{t("chat_welcome")}</p>
        </div>
        {chat.messages.map((message) => (
          <MessageBubble key={message.id} message={message} zonesById={zonesById} />
        ))}
        {chat.isSending && (
          <div
            className="me-8 flex w-fit items-center gap-1 rounded-2xl border border-edge bg-panel-2 px-3 py-2.5"
            aria-label={t("chat_thinking")}
          >
            <span className="typing-dot size-1.5 rounded-full bg-ink-dim" />
            <span className="typing-dot size-1.5 rounded-full bg-ink-dim" />
            <span className="typing-dot size-1.5 rounded-full bg-ink-dim" />
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="flex flex-col gap-2 border-t border-edge p-3">
        <QuickActions onSend={(message) => void chat.send(message)} disabled={chat.isSending} />
        <form onSubmit={submit} className="flex gap-2">
          <input
            type="text"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={t("chat_placeholder")}
            aria-label={t("chat_placeholder")}
            maxLength={500}
            className="min-w-0 flex-1 rounded-xl border border-edge bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-dim/70"
          />
          <button
            type="submit"
            disabled={chat.isSending || !draft.trim()}
            className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-surface hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {t("chat_send")}
          </button>
        </form>
      </div>
    </section>
  );
}
