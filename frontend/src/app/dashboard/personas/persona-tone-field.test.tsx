/**
 * The tone sliders: visible value, keyboard focus and announced percentage.
 *
 * Gherkin: tests/features/personas-polish-ae0513.feature
 */
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import type { ToneKey } from "@/schemas/persona";
import { PersonaToneField } from "./persona-tone-field";

function StatefulTone(): React.ReactElement {
  const [tone, setTone] = useState<Record<ToneKey, number>>({
    formal: 0.3,
    conversational: 0.8,
    humorous: 0.5,
  });
  return (
    <PersonaToneField
      tone={tone}
      onChange={(key, value) => setTone((prev) => ({ ...prev, [key]: value }))}
    />
  );
}

describe("PersonaToneField", () => {
  it("is reachable by keyboard and shows and announces its value", async () => {
    // Scenario: Tone sliders show their value and work from the keyboard
    const user = userEvent.setup();
    render(<StatefulTone />);
    await user.tab();
    const formal = screen.getByRole("slider", { name: "Formal" });
    expect(formal).toHaveFocus();
    expect(formal).toHaveAttribute("aria-valuetext", "30%");
    expect(formal).toHaveClass("focus-visible:ring-2", "h-11");
    expect(screen.getByTestId("persona-tone-formal-value")).toHaveTextContent(
      "30%",
    );
    await user.tab();
    expect(
      screen.getByRole("slider", { name: "Conversational" }),
    ).toHaveFocus();
  });

  it("updates the shown percentage when the value changes", () => {
    // Scenario: Tone sliders show their value and work from the keyboard
    render(<StatefulTone />);
    const humorous = screen.getByRole("slider", { name: "Humorous" });
    fireEvent.change(humorous, { target: { value: "0.65" } });
    expect(humorous).toHaveAttribute("aria-valuetext", "65%");
    expect(screen.getByTestId("persona-tone-humorous-value")).toHaveTextContent(
      "65%",
    );
  });
});
