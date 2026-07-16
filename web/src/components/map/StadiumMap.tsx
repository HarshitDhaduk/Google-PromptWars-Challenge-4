"use client";

/**
 * Schematic SVG map of MetLife Stadium driven entirely by service data:
 * zones colored by live crowd level, plus chat-driven overlays (route
 * polyline, amenity markers, pulsing zone highlight).
 */

import { useMemo } from "react";

import { zoneMapLabel } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type {
  CrowdResponse,
  StadiumResponse,
  Zone,
} from "../../lib/types";
import type { MapOverlay } from "../../lib/uiActions";

const CATEGORY_ICONS: Record<string, string> = {
  food: "🍽️",
  restroom: "🚻",
  water: "💧",
  first_aid: "⛑️",
  prayer: "🕌",
  info: "ℹ️",
  merch: "🛍️",
  sensory_room: "🤫",
};

const ZONE_RADIUS: Record<Zone["kind"], number> = {
  gate: 19,
  concourse: 17,
  section: 15,
  transit: 18,
};

function crowdColor(label: string | undefined): string {
  return label ? `var(--color-crowd-${label})` : "var(--color-edge)";
}

export function StadiumMap({
  stadium,
  crowd,
  overlay,
}: {
  stadium: StadiumResponse;
  crowd: CrowdResponse | null;
  overlay: MapOverlay;
}) {
  const { t } = useI18n();

  const zonesById = useMemo(() => {
    const map = new Map<string, Zone>();
    for (const zone of stadium.zones) map.set(zone.id, zone);
    return map;
  }, [stadium.zones]);

  const highlightedAmenities = overlay.amenities;
  const amenityGroups = useMemo(() => {
    const groups = new Map<string, typeof highlightedAmenities>();
    for (const amenity of highlightedAmenities) {
      const group = groups.get(amenity.zone_id) ?? [];
      group.push(amenity);
      groups.set(amenity.zone_id, group);
    }
    return groups;
  }, [highlightedAmenities]);

  const routePoints = overlay.route?.polyline ?? [];
  const routeStart = routePoints[0];
  const routeEnd = routePoints.length > 1 ? routePoints[routePoints.length - 1] : undefined;

  return (
    <svg
      viewBox={stadium.stadium.viewbox}
      role="img"
      aria-label={t("map_title")}
      className="h-auto w-full select-none"
    >
      <title>{`${t("map_title")} - ${stadium.stadium.name}`}</title>

      {/* Stadium bowl decoration */}
      <ellipse cx={500} cy={350} rx={455} ry={305} fill="none" stroke="var(--color-edge)" strokeWidth={2} opacity={0.7} />
      <ellipse cx={500} cy={350} rx={330} ry={205} fill="none" stroke="var(--color-edge)" strokeWidth={1.5} opacity={0.5} />
      <g aria-hidden>
        <rect x={365} y={293} width={270} height={114} rx={8} fill="var(--color-accent-2)" opacity={0.05} />
        <rect x={365} y={293} width={270} height={114} rx={8} fill="none" stroke="var(--color-edge)" opacity={0.8} />
        <line x1={500} y1={293} x2={500} y2={407} stroke="var(--color-edge)" opacity={0.8} />
        <circle cx={500} cy={350} r={22} fill="none" stroke="var(--color-edge)" opacity={0.8} />
      </g>

      {/* Walkways and vertical circulation */}
      <g aria-hidden>
        {stadium.edges.map((edge) => {
          const from = zonesById.get(edge.from);
          const to = zonesById.get(edge.to);
          if (!from || !to) return null;
          return (
            <line
              key={edge.id}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="var(--color-edge)"
              strokeWidth={2}
              strokeDasharray={edge.kind === "walkway" ? undefined : "3 5"}
              opacity={0.55}
            />
          );
        })}
      </g>

      {/* Chat-driven route */}
      {routePoints.length > 1 && (
        <g aria-hidden>
          <polyline
            points={routePoints.map((point) => `${point.x},${point.y}`).join(" ")}
            fill="none"
            stroke="var(--color-accent)"
            strokeWidth={6}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="route-path"
          />
          {routeStart && (
            <circle cx={routeStart.x} cy={routeStart.y} r={7} fill="var(--color-accent)" stroke="var(--color-surface)" strokeWidth={2.5} />
          )}
          {routeEnd && (
            <g>
              <circle cx={routeEnd.x} cy={routeEnd.y} r={12} fill="none" stroke="var(--color-accent)" strokeWidth={3} />
              <circle cx={routeEnd.x} cy={routeEnd.y} r={4.5} fill="var(--color-accent)" />
            </g>
          )}
        </g>
      )}

      {/* Zones colored by live crowd level */}
      {stadium.zones.map((zone) => {
        const info = crowd?.zones[zone.id];
        const color = crowdColor(info?.label);
        const radius = ZONE_RADIUS[zone.kind];
        const crowdText = info ? t(`crowd_${info.label}`) : "";
        return (
          <g key={zone.id}>
            {overlay.pulseZoneId === zone.id && (
              <circle
                cx={zone.x}
                cy={zone.y}
                r={radius + 7}
                fill="none"
                stroke="var(--color-accent-2)"
                strokeWidth={3}
                className="zone-pulse"
              />
            )}
            <circle cx={zone.x} cy={zone.y} r={radius} fill={color} opacity={0.22} />
            <circle cx={zone.x} cy={zone.y} r={radius} fill="none" stroke={color} strokeWidth={2.5} />
            <title>{crowdText ? `${zone.name} - ${crowdText}` : zone.name}</title>
            <text
              x={zone.x}
              y={zone.y + radius + 13}
              textAnchor="middle"
              fontSize={11}
              fill="var(--color-ink-dim)"
            >
              {zoneMapLabel(zone)}
            </text>
          </g>
        );
      })}

      {/* Chat-driven amenity markers */}
      {[...amenityGroups.entries()].map(([zoneId, amenities]) => {
        const zone = zonesById.get(zoneId);
        if (!zone) return null;
        return amenities.map((amenity, index) => {
          const offsetX = (index - (amenities.length - 1) / 2) * 40;
          return (
            <g
              key={amenity.id}
              transform={`translate(${zone.x + offsetX}, ${zone.y - 36})`}
            >
              <title>{`${amenity.name} · ${t("map_walk_eta", { minutes: amenity.eta_minutes })}`}</title>
              <circle r={15} fill="var(--color-panel)" stroke="var(--color-accent-2)" strokeWidth={2} />
              <text textAnchor="middle" dy={5} fontSize={14} aria-hidden>
                {CATEGORY_ICONS[amenity.category] ?? "📍"}
              </text>
              <text
                textAnchor="middle"
                y={28}
                fontSize={10}
                fontWeight={600}
                fill="var(--color-accent-2)"
              >
                {t("map_walk_eta", { minutes: amenity.eta_minutes })}
              </text>
            </g>
          );
        });
      })}
    </svg>
  );
}
