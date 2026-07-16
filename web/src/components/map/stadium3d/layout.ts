/**
 * Pure geometry for the 3D stadium: section sectors around two elliptical
 * tiers, concourse slabs, gates, and the transit plaza. No three.js here -
 * everything is plain data so it can be unit-tested.
 *
 * World axes (top view): +x = east, +z = south, y = up. Pitch at the origin.
 */

import type { Zone } from "../../../lib/types";

export interface TierSpec {
  innerRx: number;
  innerRy: number;
  outerRx: number;
  outerRy: number;
  baseY: number;
  height: number;
}

export const TIERS: Record<100 | 300, TierSpec> = {
  100: { innerRx: 78, innerRy: 60, outerRx: 106, outerRy: 84, baseY: 0, height: 10 },
  300: { innerRx: 112, innerRy: 88, outerRx: 146, outerRy: 118, baseY: 14, height: 15 },
};

export type Quadrant = "n" | "e" | "s" | "w";

export const QUADRANT_ANGLE: Record<Quadrant, number> = {
  n: -Math.PI / 2,
  e: 0,
  s: Math.PI / 2,
  w: Math.PI,
};

export const CLUSTER_SPAN = (70 * Math.PI) / 180;
const SECTION_GAP_FRACTION = 0.12;

// Keep in sync with the cluster ids in service/app/data/stadium.json.
const CLUSTER_QUADRANT: Record<string, Quadrant> = {
  sec_111_117: "n",
  sec_120_126: "e",
  sec_133_139: "s",
  sec_144_150: "w",
  sec_311_317: "n",
  sec_320_326: "e",
  sec_333_339: "s",
  sec_344_350: "w",
};

export interface AnnulusSector {
  angleStart: number;
  angleEnd: number;
  innerRx: number;
  innerRy: number;
  outerRx: number;
  outerRy: number;
}

export interface SectionSector extends AnnulusSector {
  section: string;
  clusterZoneId: string;
  level: 100 | 300;
  tier: TierSpec;
}

export function buildSectionSectors(zones: Zone[]): SectionSector[] {
  const sectors: SectionSector[] = [];
  for (const zone of zones) {
    if (zone.kind !== "section" || !zone.sections) continue;
    const quadrant = CLUSTER_QUADRANT[zone.id];
    const tier = TIERS[zone.level as 100 | 300];
    if (!quadrant || !tier) continue;

    const center = QUADRANT_ANGLE[quadrant];
    const width = CLUSTER_SPAN / zone.sections.length;
    const inset = (width * SECTION_GAP_FRACTION) / 2;
    zone.sections.forEach((section, index) => {
      const start = center - CLUSTER_SPAN / 2 + index * width;
      sectors.push({
        section,
        clusterZoneId: zone.id,
        level: zone.level as 100 | 300,
        angleStart: start + inset,
        angleEnd: start + width - inset,
        innerRx: tier.innerRx,
        innerRy: tier.innerRy,
        outerRx: tier.outerRx,
        outerRy: tier.outerRy,
        tier,
      });
    });
  }
  return sectors;
}

/**
 * Outline of an elliptical ring sector in the XZ plane (returned as x/y
 * pairs for a 2D shape): outer arc forward, inner arc back.
 */
export function sectorOutline(sector: AnnulusSector, steps = 8): { x: number; y: number }[] {
  const points: { x: number; y: number }[] = [];
  for (let index = 0; index <= steps; index += 1) {
    const angle =
      sector.angleStart + ((sector.angleEnd - sector.angleStart) * index) / steps;
    points.push({ x: Math.cos(angle) * sector.outerRx, y: Math.sin(angle) * sector.outerRy });
  }
  for (let index = steps; index >= 0; index -= 1) {
    const angle =
      sector.angleStart + ((sector.angleEnd - sector.angleStart) * index) / steps;
    points.push({ x: Math.cos(angle) * sector.innerRx, y: Math.sin(angle) * sector.innerRy });
  }
  return points;
}

export function sectorCentroid(sector: SectionSector): { x: number; y: number; z: number } {
  const angle = (sector.angleStart + sector.angleEnd) / 2;
  const rx = (sector.innerRx + sector.outerRx) / 2;
  const ry = (sector.innerRy + sector.outerRy) / 2;
  return {
    x: Math.cos(angle) * rx,
    y: sector.tier.baseY + sector.tier.height,
    z: Math.sin(angle) * ry,
  };
}

export interface ConcourseSlab extends AnnulusSector {
  zoneId: string;
  baseY: number;
  height: number;
}

const CONCOURSE_SPAN = (84 * Math.PI) / 180;

export function buildConcourseSlabs(): ConcourseSlab[] {
  const slabs: ConcourseSlab[] = [];
  for (const quadrant of ["n", "e", "s", "w"] as const) {
    const center = QUADRANT_ANGLE[quadrant];
    const angleStart = center - CONCOURSE_SPAN / 2;
    const angleEnd = center + CONCOURSE_SPAN / 2;
    slabs.push({
      zoneId: `conc_100_${quadrant}`,
      angleStart,
      angleEnd,
      innerRx: 107,
      innerRy: 85,
      outerRx: 117,
      outerRy: 93,
      baseY: 0,
      height: 2.5,
    });
    slabs.push({
      zoneId: `conc_300_${quadrant}`,
      angleStart,
      angleEnd,
      innerRx: 147,
      innerRy: 119,
      outerRx: 157,
      outerRy: 127,
      baseY: 14,
      height: 2.5,
    });
  }
  return slabs;
}

export interface GroundMarker {
  zoneId: string;
  x: number;
  z: number;
}

const GATE_RADIUS_X = 128;
const GATE_RADIUS_Y = 102;

export function gateMarkers(): GroundMarker[] {
  const angles: [string, number][] = [
    ["gate_a", (-3 * Math.PI) / 4],
    ["gate_b", -Math.PI / 4],
    ["gate_c", Math.PI / 4],
    ["gate_d", (3 * Math.PI) / 4],
  ];
  return angles.map(([zoneId, angle]) => ({
    zoneId,
    x: Math.cos(angle) * GATE_RADIUS_X,
    z: Math.sin(angle) * GATE_RADIUS_Y,
  }));
}

export const TRANSIT_MARKER: GroundMarker = { zoneId: "transit_hub", x: 0, z: 158 };
