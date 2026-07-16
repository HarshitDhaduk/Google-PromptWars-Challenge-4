import { describe, expect, it } from "vitest";

import type { Zone } from "../../../lib/types";
import {
  buildConcourseSlabs,
  buildSectionSectors,
  CLUSTER_SPAN,
  gateMarkers,
  QUADRANT_ANGLE,
  sectorCentroid,
  sectorOutline,
} from "./layout";

function clusterZone(id: string, level: number, sections: string[]): Zone {
  return { id, name: id, kind: "section", level, x: 0, y: 0, sections };
}

const ZONES: Zone[] = [
  clusterZone("sec_111_117", 100, ["111", "112", "113", "114", "115", "116", "117"]),
  clusterZone("sec_120_126", 100, ["120", "121", "122", "123", "124", "125", "126"]),
  clusterZone("sec_133_139", 100, ["133", "134", "135", "136", "137", "138", "139"]),
  clusterZone("sec_144_150", 100, ["144", "145", "146", "147", "148", "149", "150"]),
  clusterZone("sec_311_317", 300, ["311", "312", "313", "314", "315", "316", "317"]),
  clusterZone("sec_320_326", 300, ["320", "321", "322", "323", "324", "325", "326"]),
  clusterZone("sec_333_339", 300, ["333", "334", "335", "336", "337", "338", "339"]),
  clusterZone("sec_344_350", 300, ["344", "345", "346", "347", "348", "349", "350"]),
];

describe("buildSectionSectors", () => {
  const sectors = buildSectionSectors(ZONES);

  it("creates 56 sectors, 28 per tier", () => {
    expect(sectors).toHaveLength(56);
    expect(sectors.filter((sector) => sector.level === 100)).toHaveLength(28);
    expect(sectors.filter((sector) => sector.level === 300)).toHaveLength(28);
  });

  it("keeps every sector inside its cluster arc, in ascending angular order", () => {
    for (const clusterId of ["sec_320_326", "sec_133_139"]) {
      const cluster = sectors.filter((sector) => sector.clusterZoneId === clusterId);
      expect(cluster).toHaveLength(7);
      const starts = cluster.map((sector) => sector.angleStart);
      expect([...starts].sort((a, b) => a - b)).toEqual(starts);
      for (const sector of cluster) {
        expect(sector.angleEnd).toBeGreaterThan(sector.angleStart);
      }
    }
    const east = sectors.filter((sector) => sector.clusterZoneId === "sec_320_326");
    const arcStart = QUADRANT_ANGLE.e - CLUSTER_SPAN / 2;
    const arcEnd = QUADRANT_ANGLE.e + CLUSTER_SPAN / 2;
    expect(Math.min(...east.map((sector) => sector.angleStart))).toBeGreaterThanOrEqual(arcStart);
    expect(Math.max(...east.map((sector) => sector.angleEnd))).toBeLessThanOrEqual(arcEnd);
  });

  it("places the upper-east centroid east of the pitch and above the tier base", () => {
    const sector = sectors.find((entry) => entry.section === "324")!;
    const centroid = sectorCentroid(sector);
    expect(centroid.x).toBeGreaterThan(sector.innerRx * 0.5);
    expect(centroid.y).toBeGreaterThan(sector.tier.baseY);
    expect(Math.abs(centroid.z)).toBeLessThan(centroid.x);
  });
});

describe("sectorOutline", () => {
  it("returns a closed ring outline with 2*(steps+1) points", () => {
    const outline = sectorOutline(
      { angleStart: 0, angleEnd: Math.PI / 4, innerRx: 10, innerRy: 8, outerRx: 20, outerRy: 16 },
      8,
    );
    expect(outline).toHaveLength(18);
    const radii = outline.map((point) => Math.hypot(point.x, point.y));
    expect(Math.max(...radii)).toBeLessThanOrEqual(20.0001);
    expect(Math.min(...radii)).toBeGreaterThanOrEqual(7.9999);
  });
});

describe("fixed markers", () => {
  it("provides four gates in distinct diagonal quadrants", () => {
    const gates = gateMarkers();
    expect(gates).toHaveLength(4);
    const signatures = new Set(gates.map((gate) => `${Math.sign(gate.x)}:${Math.sign(gate.z)}`));
    expect(signatures.size).toBe(4);
  });

  it("builds concourse slabs for both levels of all four quadrants", () => {
    const slabs = buildConcourseSlabs();
    expect(slabs).toHaveLength(8);
    expect(new Set(slabs.map((slab) => slab.zoneId)).size).toBe(8);
  });
});
