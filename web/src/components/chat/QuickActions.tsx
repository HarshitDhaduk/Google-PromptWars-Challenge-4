"use client";

import { useI18n } from "../../lib/i18n";

const ACTIONS = [
  { icon: "🎫", labelKey: "qa_seat", messageKey: "qa_seat_message" },
  { icon: "🥙", labelKey: "qa_food", messageKey: "qa_food_message" },
  { icon: "🚻", labelKey: "qa_restroom", messageKey: "qa_restroom_message" },
  { icon: "♿", labelKey: "qa_access", messageKey: "qa_access_message" },
  { icon: "🚆", labelKey: "qa_leave", messageKey: "qa_leave_message" },
] as const;

export function QuickActions({
  onSend,
  disabled,
}: {
  onSend: (message: string) => void;
  disabled: boolean;
}) {
  const { t } = useI18n();

  return (
    <div className="flex flex-wrap gap-1.5">
      {ACTIONS.map((action) => (
        <button
          key={action.labelKey}
          type="button"
          disabled={disabled}
          onClick={() => onSend(t(action.messageKey))}
          className="inline-flex items-center gap-1.5 rounded-full border border-edge bg-panel px-3 py-1.5 text-xs text-ink hover:border-accent/60 hover:bg-panel-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span aria-hidden>{action.icon}</span>
          {t(action.labelKey)}
        </button>
      ))}
    </div>
  );
}
