import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import pt from "@/i18n/locales/pt.json";
import { buildCalendarDaysFromApi } from "@/modules/editorial-operations";
import type { CalendarItem } from "@/modules/editorial";
import { CalendarGrid } from "./calendar-grid";
import { CalendarHeader } from "./calendar-header";

const OCTOBER = new Date(2026, 9, 1);

function item(title: string): CalendarItem {
  return {
    id: `id-${title}`,
    content_type: "carousel",
    title,
    status: "draft",
    event_date: "2026-10-15",
  };
}

describe("calendar grid accessibility", () => {
  // Scenario: The month is a named table of week rows
  it("is a named table of a header row and week rows of 7 cells", () => {
    render(
      <CalendarGrid
        label="October 2026"
        days={buildCalendarDaysFromApi(OCTOBER, [], null)}
      />,
    );
    const grid = screen.getByRole("table", { name: "October 2026" });
    const rows = within(grid).getAllByRole("row");
    expect(within(rows[0]!).getAllByRole("columnheader")).toHaveLength(7);
    for (const row of rows.slice(1)) {
      expect(within(row).getAllByRole("cell")).toHaveLength(7);
    }
    expect(within(grid).getAllByRole("cell")).toHaveLength(
      (rows.length - 1) * 7,
    );
  });

  // Scenario: The read-only month adds no tab stops
  it("has no focusable cells or chips and no chip posing as a button", () => {
    const { container } = render(
      <CalendarGrid
        label="October 2026"
        days={buildCalendarDaysFromApi(OCTOBER, [item("Launch")], null)}
      />,
    );
    expect(container.querySelectorAll("[tabindex]")).toHaveLength(0);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByTitle("Launch")).toHaveTextContent("Launch");
  });

  // Scenario: An empty month is still a valid table
  it("puts the empty-month message in a row-wide cell", () => {
    const days = buildCalendarDaysFromApi(OCTOBER, [], null).map((day) => ({
      ...day,
      cur: false,
    }));
    render(<CalendarGrid label="October 2026" days={days} />);
    const message = screen.getByText("No scheduled content this month");
    const cell = message.closest('[role="cell"]');
    expect(cell).toHaveAttribute("aria-colspan", "7");
    expect(message.closest('[role="row"]')).not.toBeNull();
  });

  // Scenario: The calendar page has a level-1 heading
  it("makes the header title the page heading", () => {
    render(<CalendarHeader loading={false} onSchedule={() => undefined} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Calendar",
    );
    expect(pt.workflow.calendar.heading).toBe("Calendário");
  });

  // Scenario: Placeholder titles fall back to the localized Untitled
  it.each([["slide"], ["Slide 3"]])("shows Untitled for %s", (title) => {
    render(
      <CalendarGrid
        label="October 2026"
        days={buildCalendarDaysFromApi(OCTOBER, [item(title)], null)}
      />,
    );
    expect(screen.getByTitle("Untitled")).toHaveTextContent("Untitled");
  });
});
