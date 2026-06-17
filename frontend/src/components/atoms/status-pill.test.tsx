/**
 * AE-0154: shared StatusPill atom (extracted from the persona + rubric badges).
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusPill } from "./status-pill";

describe("StatusPill", () => {
  it("renders the label", () => {
    render(<StatusPill label="active" color="#0ff" background="#012" />);
    expect(screen.getByText("active")).toBeInTheDocument();
  });

  it("applies the foreground colour and dimmed background", () => {
    render(<StatusPill label="inactive" color="#fa0" background="#210" />);
    const pill = screen.getByText("inactive");
    expect(pill).toHaveStyle({ color: "#fa0", background: "#210" });
  });
});
