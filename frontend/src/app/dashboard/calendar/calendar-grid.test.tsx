import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildCalendarDaysFromApi } from "@/modules/editorial-operations";
import type { CalendarItem } from "@/modules/editorial";
import pt from "@/i18n/locales/pt.json";
import { CalendarGrid } from "./calendar-grid";

function item(title: string): CalendarItem {
  return {
    id: `id-${title}`,
    content_type: "carousel",
    title,
    status: "draft",
    event_date: "2026-10-15",
  };
}

function renderMonth(items: CalendarItem[]): void {
  render(
    <CalendarGrid
      days={buildCalendarDaysFromApi(new Date(2026, 9, 1), items)}
    />,
  );
}

describe("CalendarGrid chips", () => {
  // Scenario: Emphasis markup in a title is not shown as raw HTML
  it("shows a title without its emphasis markup", () => {
    renderMonth([
      item(
        "Por que todo mundo usa <strong>ChatGPT</strong> e não o **Claude**?",
      ),
    ]);
    expect(
      screen.getByRole("button", {
        name: "Por que todo mundo usa ChatGPT e não o Claude?",
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/<strong>/)).not.toBeInTheDocument();
  });

  // Scenario: An item without a title shows a localized placeholder
  it("names an untitled item with the placeholder", () => {
    renderMonth([item(""), item("   ")]);
    expect(screen.getAllByRole("button", { name: "Untitled" })).toHaveLength(2);
    expect(pt.workflow.calendar.untitled).toBe("Sem título");
  });

  // Scenario: Every chip has an accessible name and a tooltip
  it("gives every chip its title as a tooltip", () => {
    renderMonth([
      item("Gemini 4 Argon chegou. Meses de código viraram semanas."),
    ]);
    const chip = screen.getByRole("button", {
      name: "Gemini 4 Argon chegou. Meses de código viraram semanas.",
    });
    expect(chip).toHaveAttribute(
      "title",
      "Gemini 4 Argon chegou. Meses de código viraram semanas.",
    );
  });
});
