import { describe, expect, it } from "vitest";

import { deriveOverlay, parseUiActions } from "./uiActions";

const validRoute = {
  type: "show_route",
  route: {
    from_zone: "gate_c",
    to_zone: "sec_320_326",
    accessible: false,
    total_seconds: 540,
    steps: [
      {
        zone_id: "gate_c",
        name: "Gate C (Southeast)",
        edge_kind: null,
        seconds: 0,
        congestion: "moderate",
        instruction_en: "Enter through Gate C (Southeast)",
      },
    ],
    polyline: [{ x: 830, y: 560 }],
  },
};

describe("parseUiActions", () => {
  it("accepts a valid show_route action", () => {
    const actions = parseUiActions([validRoute]);
    expect(actions).toHaveLength(1);
    expect(actions[0].type).toBe("show_route");
  });

  it("ignores unknown action types and malformed entries without throwing", () => {
    const actions = parseUiActions([
      { type: "launch_fireworks", intensity: 11 },
      { type: "show_route", route: { nope: true } },
      validRoute,
      "garbage",
    ]);
    expect(actions).toHaveLength(1);
  });

  it("returns an empty list for non-array input", () => {
    expect(parseUiActions({ type: "show_route" })).toEqual([]);
  });
});

describe("deriveOverlay", () => {
  it("keeps the latest action of each kind", () => {
    const overlay = deriveOverlay(
      parseUiActions([
        validRoute,
        { type: "highlight_zone", zone_id: "transit_hub" },
      ]),
    );
    expect(overlay.route?.to_zone).toBe("sec_320_326");
    expect(overlay.pulseZoneId).toBe("transit_hub");
    expect(overlay.amenities).toEqual([]);
  });
});
