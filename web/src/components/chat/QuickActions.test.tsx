import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LocaleProvider } from "../../lib/i18n";
import { QuickActions } from "./QuickActions";

function renderWithLocale(ui: React.ReactElement) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("QuickActions", () => {
  it("renders the five localized quick-action chips", () => {
    renderWithLocale(<QuickActions onSend={() => {}} disabled={false} />);

    for (const label of [
      "Find my seat",
      "Halal food nearby",
      "Restrooms nearby",
      "Accessible route",
      "When should I leave?",
    ]) {
      expect(screen.getByRole("button", { name: new RegExp(label) })).toBeInTheDocument();
    }
  });

  it("sends the localized prompt when a chip is clicked", () => {
    const onSend = vi.fn();
    renderWithLocale(<QuickActions onSend={onSend} disabled={false} />);

    fireEvent.click(screen.getByRole("button", { name: /Find my seat/ }));
    expect(onSend).toHaveBeenCalledWith("Take me to my seat");
  });

  it("disables every chip while a message is in flight", () => {
    renderWithLocale(<QuickActions onSend={() => {}} disabled />);

    for (const button of screen.getAllByRole("button")) {
      expect(button).toBeDisabled();
    }
  });
});
