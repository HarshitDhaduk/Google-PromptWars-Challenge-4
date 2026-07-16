"use client";

import { formatStadiumTime } from "../lib/format";
import { useI18n } from "../lib/i18n";
import type { ContextResponse } from "../lib/types";

export function TicketCard({ context }: { context: ContextResponse }) {
  const { t, locale } = useI18n();
  const { match, ticket } = context;

  const cells = [
    { label: t("ticket_section"), value: ticket.section },
    { label: t("ticket_row"), value: ticket.row },
    { label: t("ticket_seat"), value: ticket.seat },
    { label: t("ticket_gate"), value: ticket.gate },
  ];

  return (
    <section
      aria-label={t("ticket_title")}
      className="rounded-2xl border border-edge bg-gradient-to-br from-panel-2 to-panel p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-widest text-ink-dim">{match.stage}</p>
        <span aria-hidden className="rounded-full border border-edge px-2 py-0.5 text-xs text-ink-dim">
          🏆
        </span>
      </div>
      <p className="mt-1 text-lg font-bold">
        {match.home} <span className="font-normal text-ink-dim">vs</span> {match.away}
      </p>
      <p className="text-xs text-ink-dim">
        {match.venue} · {match.city}
      </p>

      <dl className="mt-3 grid grid-cols-4 gap-2 border-t border-dashed border-edge pt-3 text-center">
        {cells.map((cell) => (
          <div key={cell.label}>
            <dt className="text-[10px] uppercase tracking-wider text-ink-dim">{cell.label}</dt>
            <dd className="text-xl font-bold text-accent">{cell.value}</dd>
          </div>
        ))}
      </dl>

      <p className="mt-3 text-xs text-ink-dim">
        {t("ticket_kickoff")}: {formatStadiumTime(match.kickoff_utc, locale)} ET
      </p>
    </section>
  );
}
