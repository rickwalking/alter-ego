import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NeonLogoMark } from "./neon-logo-mark";

describe("NeonLogoMark", () => {
  it("renders the mark with the given glow", () => {
    // Scenario: visible mark
    render(<NeonLogoMark boxShadow="0 0 1px red" />);
    const mark = screen.getByText("P");
    expect(mark).toHaveStyle({ boxShadow: "0 0 1px red" });
    expect(mark).not.toHaveAttribute("aria-hidden");
  });

  it("hides a decorative mark from assistive tech", () => {
    // Scenario: decorative mark
    render(<NeonLogoMark boxShadow="none" decorative />);
    expect(screen.getByText("P")).toHaveAttribute("aria-hidden", "true");
  });
});
