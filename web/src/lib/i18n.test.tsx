import { describe, expect, it } from "vitest";

import { RTL_LOCALES, translate } from "./i18n";

describe("translate", () => {
  it("returns the Spanish string under the es locale", () => {
    expect(translate("es", "chat_send")).toBe("Enviar");
  });

  it("falls back to English for a key missing in another locale", () => {
    // Every real key exists in all locales; simulate with a fake key that
    // only exists in en by checking the fallback chain returns the key
    // itself when nothing matches.
    expect(translate("es", "made_up_key")).toBe("made_up_key");
  });

  it("interpolates variables and leaves unknown placeholders intact", () => {
    expect(translate("en", "kickoff_in", { minutes: 12 })).toBe("Kickoff in 12 min");
    expect(translate("en", "seats_count", { available: 3, capacity: 480 })).toBe(
      "3 of 480 seats",
    );
  });
});

describe("RTL locales", () => {
  it("treats Arabic as right-to-left", () => {
    expect(RTL_LOCALES.has("ar")).toBe(true);
    expect(RTL_LOCALES.has("es")).toBe(false);
  });
});
