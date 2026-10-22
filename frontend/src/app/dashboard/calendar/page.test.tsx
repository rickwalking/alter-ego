import { render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import CalendarPage from "./page";

vi.mock("@/modules/editorial", () => ({
  useContentCalendar: () => ({ calendar: null, loading: false, error: null }),
}));

describe("CalendarPage today", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  // Scenario: The server render highlights no day
  it("renders no month grid on the server", () => {
    const html = renderToString(<CalendarPage />);
    expect(html).not.toMatch(/<div[^>]*role="gridcell"/);
  });

  // Scenario: Today is the viewer's local date after the page loads
  it("highlights the local day in the browser", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 21, 21, 30));
    render(<CalendarPage />);
    expect(screen.getByText("October 2026")).toBeInTheDocument();
    const highlighted = screen
      .getAllByRole("gridcell")
      .filter((cell) => cell.style.border !== "");
    expect(highlighted.map((cell) => cell.textContent.trim())).toEqual(["21"]);
  });
});
