"use client";

/**
 * Chat state: session identity, message list, send flow, and hand-off of
 * validated ui_actions to the map.
 */

import { useCallback, useRef, useState } from "react";

import { ApiError, postChat } from "../lib/api";
import type { Locale, ToolCallMeta, TurnProvider } from "../lib/types";
import { parseUiActions, type UiAction } from "../lib/uiActions";

const SESSION_KEY = "stadium-copilot-session";

export type ChatErrorKind = "rate" | "service" | "generic";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  toolCalls?: ToolCallMeta[];
  provider?: TurnProvider;
  uiActions?: UiAction[];
  errorKind?: ChatErrorKind;
}

export interface ChatState {
  messages: ChatMessage[];
  isSending: boolean;
  send: (text: string) => Promise<void>;
}

function getSessionId(): string {
  const existing = window.sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const created = crypto.randomUUID();
  window.sessionStorage.setItem(SESSION_KEY, created);
  return created;
}

function errorKindFor(error: unknown): ChatErrorKind {
  if (error instanceof ApiError) {
    if (error.status === 429) return "rate";
    if (error.status === 503 || error.code === "network") return "service";
  }
  return "generic";
}

export function useChat(
  locale: Locale,
  onUiActions: (actions: UiAction[]) => void,
): ChatState {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const counterRef = useRef(0);

  const nextId = useCallback(() => {
    counterRef.current += 1;
    return `msg-${counterRef.current}`;
  }, []);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) return;

      setMessages((current) => [
        ...current,
        { id: nextId(), role: "user", text: trimmed },
      ]);
      setIsSending(true);
      try {
        const response = await postChat({
          session_id: getSessionId(),
          message: trimmed.slice(0, 500),
          locale,
        });
        const uiActions = parseUiActions(response.ui_actions);
        setMessages((current) => [
          ...current,
          {
            id: nextId(),
            role: "assistant",
            text: response.reply,
            toolCalls: response.tool_calls,
            provider: response.provider,
            uiActions,
          },
        ]);
        if (uiActions.length > 0) onUiActions(uiActions);
      } catch (error) {
        setMessages((current) => [
          ...current,
          { id: nextId(), role: "assistant", text: "", errorKind: errorKindFor(error) },
        ]);
      } finally {
        setIsSending(false);
      }
    },
    [isSending, locale, nextId, onUiActions],
  );

  return { messages, isSending, send };
}
