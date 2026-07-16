/**
 * TypeScript mirrors of the Python service schemas.
 * Keep in sync with service/app/models/{entities,api}.py.
 */

export type ZoneKind = "gate" | "concourse" | "section" | "transit";
export type EdgeKind = "walkway" | "stairs" | "elevator";
export type CrowdLabel = "low" | "moderate" | "high" | "severe";
export type Phase = "pre_match" | "first_half" | "halftime" | "second_half" | "post_match";
export type Locale = "en" | "es" | "fr" | "ar" | "pt" | "de";
export type ProviderName = "gemini" | "mock";
export type TurnProvider = "gemini" | "mock" | "mock-fallback";

export const LOCALES: readonly Locale[] = ["en", "es", "fr", "ar", "pt", "de"];

export interface Zone {
  id: string;
  name: string;
  kind: ZoneKind;
  level: number;
  x: number;
  y: number;
  sections: string[] | null;
}

export interface Edge {
  id: string;
  from: string;
  to: string;
  kind: EdgeKind;
  base_seconds: number;
}

export interface Amenity {
  id: string;
  name: string;
  category: string;
  zone_id: string;
  tags: string[];
}

export interface StadiumInfo {
  name: string;
  city: string;
  viewbox: string;
}

export interface StadiumResponse {
  stadium: StadiumInfo;
  zones: Zone[];
  edges: Edge[];
  amenities: Amenity[];
}

export interface CrowdInfo {
  level: number;
  label: CrowdLabel;
  multiplier: number;
}

export interface CrowdResponse {
  sim_time: string;
  phase: Phase;
  match_minute: number | null;
  minutes_to_kickoff: number | null;
  /** Inferred fan location (gate before kickoff, seat afterwards). */
  fan_zone_id: string;
  zones: Record<string, CrowdInfo>;
}

export type SeatStatus = "sold_out" | "limited" | "available";

export interface SeatInfo {
  section: string;
  zone_id: string;
  level: number;
  capacity: number;
  available: number;
  status: SeatStatus;
}

export interface SeatsResponse {
  sim_time: string;
  phase: Phase;
  sections: Record<string, SeatInfo>;
}

export interface MatchEvent {
  minute: number;
  type: "goal";
  team: string;
  player: string;
}

export interface Match {
  id: string;
  stage: string;
  home: string;
  away: string;
  home_code: string;
  away_code: string;
  kickoff_utc: string;
  gates_open_utc: string;
  venue: string;
  city: string;
  events: MatchEvent[];
}

export interface Ticket {
  holder: string;
  match_id: string;
  section: string;
  row: string;
  seat: string;
  gate: string;
  level: number;
}

export interface SimInfo {
  sim_time: string;
  phase: Phase;
  match_minute: number | null;
  minutes_to_kickoff: number | null;
  speed: number;
}

export interface ContextResponse {
  match: Match;
  ticket: Ticket;
  sim: SimInfo;
  provider: ProviderName;
  locales: string[];
}

export interface RoutePoint {
  x: number;
  y: number;
}

export interface RouteStep {
  zone_id: string;
  name: string;
  edge_kind: EdgeKind | null;
  seconds: number;
  congestion: CrowdLabel;
  instruction_en: string;
}

export interface RouteResult {
  from_zone: string;
  to_zone: string;
  accessible: boolean;
  total_seconds: number;
  steps: RouteStep[];
  polyline: RoutePoint[];
}

export interface AmenityWithEta {
  id: string;
  name: string;
  category: string;
  zone_id: string;
  zone_name: string;
  eta_minutes: number;
  tags: string[];
}

export interface ToolCallMeta {
  name: string;
  ok: boolean;
}

export interface ChatApiResponse {
  reply: string;
  ui_actions: unknown[];
  tool_calls: ToolCallMeta[];
  provider: TurnProvider;
}
