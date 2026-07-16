"use client";

/**
 * Interactive 3D stadium: 56 seating sections in two elliptical tiers,
 * concourse slabs, gates, and the transit plaza - colored live by crowd
 * density or seat availability - plus a VR-style "watch from my seat"
 * camera and the simulated match broadcast on the pitch.
 *
 * i18n happens only in the DOM layer (HUD, panels): React context does not
 * cross into the Canvas reconciler, and the scene itself needs no text.
 */

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import {
  makeSimAnchor,
  phaseForWallMinute,
  scoreAt,
  scoreboardMinute,
  wallMinuteAt,
} from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import type {
  ContextResponse,
  CrowdLabel,
  CrowdResponse,
  SeatStatus,
  SeatsResponse,
  StadiumResponse,
} from "../../../lib/types";
import {
  buildConcourseSlabs,
  buildSectionSectors,
  gateMarkers,
  sectorCentroid,
  sectorOutline,
  TRANSIT_MARKER,
  type AnnulusSector,
  type SectionSector,
} from "./layout";
import { MatchPitch } from "./MatchPitch";

const CROWD_HEX: Record<CrowdLabel, string> = {
  low: "#10b981",
  moderate: "#f59e0b",
  high: "#f97316",
  severe: "#ef4444",
};

const SEAT_HEX: Record<SeatStatus, string> = {
  sold_out: "#42506e",
  limited: "#f59e0b",
  available: "#34d399",
};

const NEUTRAL_HEX = "#26334f";

export type ColorMode = "crowd" | "seats";

function annulusShape(annulus: AnnulusSector): THREE.Shape {
  const outline = sectorOutline(annulus);
  const shape = new THREE.Shape();
  outline.forEach((point, index) => {
    // Shape-space y is negated so that after the -90deg X rotation the
    // world +z axis points south, matching the layout convention.
    if (index === 0) shape.moveTo(point.x, -point.y);
    else shape.lineTo(point.x, -point.y);
  });
  shape.closePath();
  return shape;
}

function SectorMesh({
  annulus,
  baseY,
  height,
  color,
  highlighted = false,
  raised = false,
  onSelect,
  onHover,
}: {
  annulus: AnnulusSector;
  baseY: number;
  height: number;
  color: string;
  highlighted?: boolean;
  raised?: boolean;
  onSelect?: () => void;
  onHover?: (hovering: boolean) => void;
}) {
  const shape = useMemo(() => annulusShape(annulus), [annulus]);
  const extrudeArgs = useMemo(
    () => [shape, { depth: height, bevelEnabled: false }] as const,
    [shape, height],
  );

  return (
    <mesh
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, baseY + (raised ? 1.5 : 0), 0]}
      onClick={
        onSelect
          ? (event) => {
              event.stopPropagation();
              onSelect();
            }
          : undefined
      }
      onPointerOver={
        onHover
          ? (event) => {
              event.stopPropagation();
              onHover(true);
            }
          : undefined
      }
      onPointerOut={onHover ? () => onHover(false) : undefined}
    >
      <extrudeGeometry args={extrudeArgs} />
      <meshStandardMaterial
        color={color}
        roughness={0.65}
        emissive={highlighted ? color : "#000000"}
        emissiveIntensity={highlighted ? 0.55 : 0}
      />
    </mesh>
  );
}

function OrbitRig({ enabled }: { enabled: boolean }) {
  const { camera, gl } = useThree();
  const controlsRef = useRef<OrbitControls | null>(null);

  useEffect(() => {
    const controls = new OrbitControls(camera, gl.domElement);
    controls.enablePan = false;
    controls.enableDamping = false;
    controls.minDistance = 120;
    controls.maxDistance = 520;
    controls.minPolarAngle = 0.15;
    controls.maxPolarAngle = 1.35;
    controls.target.set(0, 6, 0);
    controls.update();
    controlsRef.current = controls;
    return () => controls.dispose();
  }, [camera, gl]);

  useEffect(() => {
    if (controlsRef.current) controlsRef.current.enabled = enabled;
  }, [enabled]);

  return null;
}

function SeatCameraRig({
  active,
  position,
}: {
  active: boolean;
  position: [number, number, number] | null;
}) {
  const goal = useMemo(
    () => (position ? new THREE.Vector3(...position) : null),
    [position],
  );
  const lookTarget = useMemo(() => new THREE.Vector3(0, 2, 0), []);

  useFrame(({ camera }) => {
    if (!active || !goal) return;
    camera.position.lerp(goal, 0.08);
    camera.lookAt(lookTarget);
  });

  return null;
}

/** Ticks the accelerated sim clock in the DOM layer (HUD scoreboard). */
function useSimWallMinute(simTimeIso: string, speed: number, kickoffUtc: string): number {
  const [minute, setMinute] = useState(0);

  useEffect(() => {
    const anchor = makeSimAnchor(simTimeIso, speed, kickoffUtc, performance.now());
    const update = () => setMinute(wallMinuteAt(anchor, performance.now()));
    update();
    const id = window.setInterval(update, 500);
    return () => window.clearInterval(id);
  }, [simTimeIso, speed, kickoffUtc]);

  return minute;
}

export default function Stadium3D({
  stadium,
  crowd,
  seats,
  context,
  onAskRoute,
}: {
  stadium: StadiumResponse;
  crowd: CrowdResponse | null;
  seats: SeatsResponse | null;
  context: ContextResponse;
  onAskRoute: (section: string) => void;
}) {
  const { t } = useI18n();
  const [mode, setMode] = useState<ColorMode>("crowd");
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [seatView, setSeatView] = useState(false);

  const sectors = useMemo(() => buildSectionSectors(stadium.zones), [stadium.zones]);
  const slabs = useMemo(() => buildConcourseSlabs(), []);
  const gates = useMemo(() => gateMarkers(), []);
  const zoneNames = useMemo(
    () => new Map(stadium.zones.map((zone) => [zone.id, zone.name])),
    [stadium.zones],
  );

  const ticketSection = context.ticket.section;
  const ticketSector = sectors.find((sector) => sector.section === ticketSection) ?? null;
  const seatCamera = useMemo<[number, number, number] | null>(() => {
    if (!ticketSector) return null;
    const centroid = sectorCentroid(ticketSector);
    return [centroid.x * 0.99, centroid.y + 6, centroid.z * 0.99];
  }, [ticketSector]);

  const fanZoneId = crowd?.fan_zone_id ?? null;
  const beacon = useMemo<[number, number, number] | null>(() => {
    if (!fanZoneId) return null;
    if (fanZoneId.startsWith("gate_")) {
      const gate = gates.find((marker) => marker.zoneId === fanZoneId);
      return gate ? [gate.x, 12, gate.z] : null;
    }
    const cluster = sectors.filter((sector) => sector.clusterZoneId === fanZoneId);
    const sector =
      cluster.find((entry) => entry.section === ticketSection) ??
      cluster[Math.floor(cluster.length / 2)];
    if (!sector) return null;
    const centroid = sectorCentroid(sector);
    return [centroid.x, centroid.y + 9, centroid.z];
  }, [fanZoneId, gates, sectors, ticketSection]);

  const simTimeIso = crowd?.sim_time ?? context.sim.sim_time;
  const wallMinute = useSimWallMinute(simTimeIso, context.sim.speed, context.match.kickoff_utc);
  const phase = phaseForWallMinute(wallMinute);
  const sbMinute = scoreboardMinute(wallMinute);
  const [homeGoals, awayGoals] = scoreAt(context.match, sbMinute);
  const activeGoal =
    sbMinute === null
      ? undefined
      : context.match.events.find((event) => Math.abs(sbMinute - event.minute) <= 1);
  const isLive = phase === "first_half" || phase === "second_half";

  const sectionColor = (sector: SectionSector): string => {
    if (mode === "seats") {
      const info = seats?.sections[sector.section];
      return info ? SEAT_HEX[info.status] : NEUTRAL_HEX;
    }
    const info = crowd?.zones[sector.clusterZoneId];
    return info ? CROWD_HEX[info.label] : NEUTRAL_HEX;
  };

  const zoneColor = (zoneId: string): string => {
    if (mode === "seats") return NEUTRAL_HEX;
    const info = crowd?.zones[zoneId];
    return info ? CROWD_HEX[info.label] : NEUTRAL_HEX;
  };

  const describe = (section: string): string => {
    const sector = sectors.find((entry) => entry.section === section);
    if (!sector) return section;
    const parts = [
      `${t("section_label")} ${section}`,
      zoneNames.get(sector.clusterZoneId) ?? sector.clusterZoneId,
    ];
    const crowdInfo = crowd?.zones[sector.clusterZoneId];
    if (crowdInfo) parts.push(t(`crowd_${crowdInfo.label}`));
    const seatInfo = seats?.sections[section];
    if (seatInfo) {
      parts.push(
        seatInfo.status === "sold_out"
          ? t("seat_sold_out")
          : t("seats_count", { available: seatInfo.available, capacity: seatInfo.capacity }),
      );
    }
    return parts.join(" · ");
  };

  const selectedSeat = selected ? (seats?.sections[selected] ?? null) : null;
  const selectedSector = selected
    ? (sectors.find((entry) => entry.section === selected) ?? null)
    : null;
  const selectedCrowd = selectedSector ? (crowd?.zones[selectedSector.clusterZoneId] ?? null) : null;

  const scoreboardText =
    phase === "pre_match"
      ? t("kickoff_in", { minutes: Math.max(1, Math.ceil(-wallMinute)) })
      : `${context.match.home_code} ${homeGoals} - ${awayGoals} ${context.match.away_code}` +
        (isLive && sbMinute !== null ? ` · ${sbMinute}'` : "");

  return (
    <div>
      {/* Controls row */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <div role="group" aria-label={t("legend_title")} className="flex rounded-lg border border-edge p-0.5">
          {(["crowd", "seats"] as const).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={mode === option}
              onClick={() => setMode(option)}
              className={`rounded-md px-2.5 py-1 text-xs ${
                mode === option ? "bg-panel-2 text-ink" : "text-ink-dim hover:text-ink"
              }`}
            >
              {t(`mode_${option}`)}
            </button>
          ))}
        </div>

        {mode === "seats" && (
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-dim">
            {(["available", "limited", "sold_out"] as const).map((status) => (
              <span key={status} className="flex items-center gap-1.5">
                <span
                  aria-hidden
                  className="size-2.5 rounded-full"
                  style={{ background: SEAT_HEX[status] }}
                />
                {t(`seat_${status}`)}
              </span>
            ))}
          </span>
        )}

        <button
          type="button"
          onClick={() => setSeatView((current) => !current)}
          className="ms-auto rounded-lg border border-accent/50 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent/20"
        >
          {seatView ? `↩ ${t("seat_view_exit")}` : `🎥 ${t("seat_view")}`}
        </button>
      </div>

      {/* Scene */}
      <div
        className={`relative h-[420px] overflow-hidden rounded-xl bg-[#0a0f1d] md:h-[500px] ${
          hovered ? "cursor-pointer" : ""
        }`}
      >
        <Canvas
          camera={{ position: [0, 210, 330], fov: 40 }}
          dpr={[1, 1.75]}
          onPointerMissed={() => setSelected(null)}
        >
          <ambientLight intensity={0.75} />
          <directionalLight position={[140, 220, 90]} intensity={1.15} />
          <OrbitRig enabled={!seatView} />
          <SeatCameraRig active={seatView} position={seatCamera} />

          {/* Ground */}
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.6, 0]} scale={[1, 0.84, 1]}>
            <circleGeometry args={[210, 48]} />
            <meshStandardMaterial color="#0c1425" roughness={1} />
          </mesh>

          <MatchPitch match={context.match} simTimeIso={simTimeIso} speed={context.sim.speed} />

          {/* Seating bowl */}
          {sectors.map((sector) => (
            <SectorMesh
              key={sector.section}
              annulus={sector}
              baseY={sector.tier.baseY}
              height={sector.tier.height}
              color={sectionColor(sector)}
              highlighted={selected === sector.section || hovered === sector.section}
              raised={selected === sector.section}
              onSelect={() =>
                setSelected((current) => (current === sector.section ? null : sector.section))
              }
              onHover={(hovering) => setHovered(hovering ? sector.section : null)}
            />
          ))}

          {/* Concourse slabs (crowd zones) */}
          {slabs.map((slab) => (
            <SectorMesh
              key={slab.zoneId}
              annulus={slab}
              baseY={slab.baseY}
              height={slab.height}
              color={zoneColor(slab.zoneId)}
            />
          ))}

          {/* Gates and transit plaza */}
          {gates.map((gate) => (
            <mesh key={gate.zoneId} position={[gate.x, 4, gate.z]}>
              <boxGeometry args={[10, 8, 10]} />
              <meshStandardMaterial color={zoneColor(gate.zoneId)} roughness={0.7} />
            </mesh>
          ))}
          <mesh position={[TRANSIT_MARKER.x, 1.5, TRANSIT_MARKER.z]}>
            <boxGeometry args={[34, 3, 12]} />
            <meshStandardMaterial color={zoneColor(TRANSIT_MARKER.zoneId)} roughness={0.7} />
          </mesh>

          {/* Fan "you are here" beacon */}
          {beacon && (
            <group position={beacon}>
              <mesh rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[2.6, 5.5, 12]} />
                <meshStandardMaterial
                  color="#fbbf24"
                  emissive="#fbbf24"
                  emissiveIntensity={0.6}
                />
              </mesh>
            </group>
          )}
        </Canvas>

        {/* HUD overlays (DOM, localized) */}
        <div className="pointer-events-none absolute inset-x-0 top-2 flex justify-center">
          <span className="flex items-center gap-2 rounded-full bg-black/60 px-3 py-1.5 text-sm font-semibold backdrop-blur">
            {isLive && (
              <span className="flex items-center gap-1 text-[10px] font-bold text-crowd-severe">
                <span className="size-1.5 animate-pulse rounded-full bg-crowd-severe motion-reduce:animate-none" />
                {t("live_label")}
              </span>
            )}
            {!isLive && phase !== "pre_match" && (
              <span className="text-[10px] font-bold uppercase text-ink-dim">
                {t(`phase_${phase}`)}
              </span>
            )}
            {scoreboardText}
          </span>
        </div>

        {activeGoal && (
          <div className="pointer-events-none absolute inset-x-0 top-1/3 flex justify-center">
            <span className="animate-pulse rounded-2xl bg-accent-2/90 px-5 py-2.5 text-xl font-black text-surface shadow-lg motion-reduce:animate-none">
              ⚽ {t("goal_banner", { player: activeGoal.player, minute: activeGoal.minute })}
            </span>
          </div>
        )}

        {fanZoneId && (
          <div className="pointer-events-none absolute start-2 top-2">
            <span className="rounded-full bg-black/60 px-2.5 py-1 text-xs text-ink backdrop-blur">
              📍 {t("you_are_here")}: {zoneNames.get(fanZoneId) ?? fanZoneId}
            </span>
          </div>
        )}

        <div className="pointer-events-none absolute inset-x-2 bottom-2 flex items-end justify-between gap-2 text-xs">
          <span className="max-w-[75%] rounded-lg bg-black/60 px-2.5 py-1.5 text-ink backdrop-blur">
            {hovered ? describe(hovered) : selected ? describe(selected) : t("hint_pick")}
          </span>
          <span className="hidden rounded-lg bg-black/60 px-2.5 py-1.5 text-ink-dim backdrop-blur md:block">
            {t("drag_hint")}
          </span>
        </div>
      </div>

      {/* Selected section details */}
      {selected && selectedSector && (
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border border-edge bg-panel-2 p-3 text-sm">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-ink-dim">
              {t("section_label")}
            </p>
            <p className="text-xl font-bold text-accent">{selected}</p>
          </div>
          <div className="text-ink-dim">
            {zoneNames.get(selectedSector.clusterZoneId)}
            <br />
            {t("level_label")} {selectedSector.level}
          </div>
          {selectedCrowd && (
            <span className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="size-2.5 rounded-full"
                style={{ background: CROWD_HEX[selectedCrowd.label] }}
              />
              {t(`crowd_${selectedCrowd.label}`)}
            </span>
          )}
          {selectedSeat && (
            <span className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="size-2.5 rounded-full"
                style={{ background: SEAT_HEX[selectedSeat.status] }}
              />
              {selectedSeat.status === "sold_out"
                ? t("seat_sold_out")
                : t("seats_count", {
                    available: selectedSeat.available,
                    capacity: selectedSeat.capacity,
                  })}
            </span>
          )}
          <div className="ms-auto">
            {selected === ticketSection ? (
              <span className="rounded-full border border-accent/50 bg-accent/10 px-3 py-1 text-xs text-accent">
                🎫 {t("your_seat")}
              </span>
            ) : (
              <button
                type="button"
                onClick={() => onAskRoute(selected)}
                className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-surface hover:opacity-90"
              >
                {t("route_here")}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
