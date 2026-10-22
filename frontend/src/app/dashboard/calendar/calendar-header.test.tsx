import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CalendarHeader } from "./calendar-header";

describe("CalendarHeader on narrow screens", () => {
  // Scenario: The calendar top bar fits a 375 px screen
  it("wraps its actions and hides the breadcrumb below sm", () => {
    const { container } = render(<CalendarHeader loading={false} />);
    expect(container.firstElementChild).toHaveClass("flex-wrap", "min-h-14");
    expect(screen.getByText("content calendar").parentElement).toHaveClass(
      "hidden",
      "sm:inline",
    );
    expect(
      screen.getByRole("button", { name: /Schedule Post/ }).parentElement,
    ).toHaveClass("w-full", "flex-wrap", "sm:w-auto");
  });
});
