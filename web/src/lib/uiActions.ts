/**
 * Runtime validation of chat ui_actions with zod.
 * Unknown action types are ignored (forward compatible), never thrown.
 */

import { z } from "zod";

const crowdLabelSchema = z.enum(["low", "moderate", "high", "severe"]);
const edgeKindSchema = z.enum(["walkway", "stairs", "elevator"]);

const routePointSchema = z.object({
  x: z.number(),
  y: z.number(),
});

const routeStepSchema = z.object({
  zone_id: z.string(),
  name: z.string(),
  edge_kind: edgeKindSchema.nullable(),
  seconds: z.number(),
  congestion: crowdLabelSchema,
  instruction_en: z.string(),
});

const routeResultSchema = z.object({
  from_zone: z.string(),
  to_zone: z.string(),
  accessible: z.boolean(),
  total_seconds: z.number(),
  steps: z.array(routeStepSchema),
  polyline: z.array(routePointSchema),
});

const amenityWithEtaSchema = z.object({
  id: z.string(),
  name: z.string(),
  category: z.string(),
  zone_id: z.string(),
  zone_name: z.string(),
  eta_minutes: z.number(),
  tags: z.array(z.string()),
});

const showRouteSchema = z.object({
  type: z.literal("show_route"),
  route: routeResultSchema,
});

const highlightAmenitiesSchema = z.object({
  type: z.literal("highlight_amenities"),
  amenities: z.array(amenityWithEtaSchema),
});

const highlightZoneSchema = z.object({
  type: z.literal("highlight_zone"),
  zone_id: z.string(),
});

export const uiActionSchema = z.discriminatedUnion("type", [
  showRouteSchema,
  highlightAmenitiesSchema,
  highlightZoneSchema,
]);

export type UiAction = z.infer<typeof uiActionSchema>;
export type ShowRouteAction = z.infer<typeof showRouteSchema>;
export type HighlightAmenitiesAction = z.infer<typeof highlightAmenitiesSchema>;
export type HighlightZoneAction = z.infer<typeof highlightZoneSchema>;

export function parseUiActions(raw: unknown): UiAction[] {
  if (!Array.isArray(raw)) return [];
  const actions: UiAction[] = [];
  for (const candidate of raw) {
    const parsed = uiActionSchema.safeParse(candidate);
    if (parsed.success) actions.push(parsed.data);
  }
  return actions;
}

export interface MapOverlay {
  route: ShowRouteAction["route"] | null;
  amenities: HighlightAmenitiesAction["amenities"];
  pulseZoneId: string | null;
}

/** Collapse an action batch into what the map should currently show. */
export function deriveOverlay(actions: UiAction[]): MapOverlay {
  const overlay: MapOverlay = { route: null, amenities: [], pulseZoneId: null };
  for (const action of actions) {
    if (action.type === "show_route") overlay.route = action.route;
    else if (action.type === "highlight_amenities") overlay.amenities = action.amenities;
    else overlay.pulseZoneId = action.zone_id;
  }
  return overlay;
}
