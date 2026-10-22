/**
 * Scenarios: tests/features/calendar-week-day-views.feature.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import userEvent from "@testing-library/user-event";
import type { CalendarItem } from "@/modules/editorial";

const nav = vi.hoisted(() => {
  const listeners = new Set<() => void>();
  const state = {
    search: "",
    listeners,
    history: [] as string[],
    replace: vi.fn((href: string) => {
      state.search = href.includes("?") ? href.slice(href.indexOf("?")) : "";
      listeners.forEach((listener) => listener());
    }),
    push: vi.fn((href: string) => {
      state.history.push(state.search);
      state.replace(href);
    }),
    back: (): void => {
      state.search = state.history.pop() ?? "";
      listeners.forEach((listener) => listener());
    },
  };
  return state;
});
const { mockUseContentCalendar } = vi.hoisted(() => ({
  mockUseContentCalendar: vi.fn(),
}));

vi.mock("next/navigation", async () => {
  const { useSyncExternalStore } = await import("react");
  const subscribe = (listener: () => void): (() => void) => {
    nav.listeners.add(listener);
    return () => nav.listeners.delete(listener);
  };
  return {
    usePathname: () => "/dashboard/calendar",
    useRouter: () => ({ replace: nav.replace, push: nav.push }),
    useSearchParams: () =>
      new URLSearchParams(
        useSyncExternalStore(
          subscribe,
          () => nav.search,
          () => nav.search,
        ),
      ),
  };
});
vi.mock("@/modules/editorial", () => ({
  useContentCalendar: mockUseContentCalendar,
}));
vi.mock("@/modules/publishing", async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useBlogPosts: () => ({ posts: [], loading: false, error: null }),
}));

import CalendarPage from "./page";

const ORIGINAL_TZ = process.env.TZ;

function restoreTimeZone(): void {
  if (ORIGINAL_TZ === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = ORIGINAL_TZ;
  }
}

function withItems(items: CalendarItem[]): void {
  mockUseContentCalendar.mockReturnValue({
    calendar: { items, start: "", end: "", total: items.length },
    loading: false,
    error: null,
  });
}

function renderPage(search: string): void {
  nav.search = search;
  render(<CalendarPage />);
}

const blogPost: CalendarItem = {
  id: "post-1",
  content_type: "carousel",
  title: "Evening post",
  status: "scheduled",
  event_date: "2026-10-22T01:00:00Z",
  phase_status: "approved",
};

describe("CalendarPage views", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 21, 12, 0));
    nav.replace.mockClear();
    nav.push.mockClear();
    nav.history = [];
    withItems([]);
  });

  afterEach(() => {
    vi.useRealTimers();
    restoreTimeZone();
  });

  // Scenario: The server render highlights no day
  it("renders no grid and no week on the server", () => {
    nav.search = "?view=week";
    const html = renderToString(<CalendarPage />);
    expect(html).not.toMatch(/<div[^>]*role="cell"/);
    expect(html).not.toMatch(/aria-current="date"/);
  });

  // Scenario: Today is the viewer's local date after the page loads
  it("highlights the local day in the browser", () => {
    vi.setSystemTime(new Date(2026, 9, 21, 21, 30));
    renderPage("");
    expect(screen.getByText("October 2026")).toBeInTheDocument();
    const highlighted = screen
      .getAllByRole("cell")
      .filter((cell) => cell.style.border !== "");
    expect(highlighted.map((cell) => cell.textContent.trim())).toEqual(["21"]);
  });

  // Scenario: The calendar opens on the month view by default
  it("opens on the month grid with Month pressed", () => {
    renderPage("");
    expect(screen.getByRole("button", { name: "Month" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getAllByRole("cell").length).toBeGreaterThan(27);
  });

  // Scenario: An unknown view in the URL falls back to the month view
  it("shows the month grid for an unknown view", () => {
    renderPage("?view=year");
    expect(screen.getAllByRole("cell").length).toBeGreaterThan(27);
  });

  // Scenario: The view switch is keyboard operable and announces the active view
  it("switches to the week view from the keyboard", async () => {
    const user = userEvent.setup();
    renderPage("");
    screen.getByRole("button", { name: "Week" }).focus();
    await user.keyboard("{Enter}");

    expect(nav.search).toBe("?view=week");
    expect(screen.getByRole("button", { name: "Week" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Month" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.queryAllByRole("cell")).toHaveLength(0);
    expect(screen.getAllByRole("listitem")).toHaveLength(7);
  });

  // Scenario: A week day header opens that day in the day view
  it("opens a day from its week header", async () => {
    const user = userEvent.setup();
    renderPage("?view=week&date=2026-10-21");
    await user.click(
      screen.getByRole("button", {
        name: "Open Thursday, October 22, 2026 in the day view",
      }),
    );
    expect(nav.search).toBe("?view=day&date=2026-10-22");
    expect(
      screen.getByRole("heading", { name: "Thursday, October 22, 2026" }),
    ).toBeInTheDocument();
  });

  // Scenario: Back returns to the previous view
  it("goes back to the week after opening a day", async () => {
    const user = userEvent.setup();
    renderPage("?view=week&date=2026-10-21");
    await user.click(
      screen.getByRole("button", {
        name: "Open Thursday, October 22, 2026 in the day view",
      }),
    );
    act(() => nav.back());
    expect(screen.getByRole("button", { name: "Week" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(7);
  });

  // Scenario: An item without a title is listed as untitled
  it("lists an untitled day item as Untitled", () => {
    withItems([{ ...blogPost, title: "", event_date: "2026-10-21" }]);
    renderPage("?view=day&date=2026-10-21");
    expect(
      within(screen.getByRole("listitem")).getByText("Untitled"),
    ).toBeInTheDocument();
  });

  it("marks today's week column as the current date", () => {
    renderPage("?view=week");
    expect(
      screen.getByRole("button", { name: /Wednesday, October 21, 2026/ }),
    ).toHaveAttribute("aria-current", "date");
  });

  // Scenario: Previous and next move by one week in the week view
  it("labels and moves the arrows by week", async () => {
    const user = userEvent.setup();
    renderPage("?view=week&date=2026-10-21");
    await user.click(screen.getByRole("button", { name: "Next week" }));
    expect(nav.search).toBe("?view=week&date=2026-10-28");
    expect(screen.getByRole("button", { name: "Previous week" })).toBeVisible();
  });

  // Scenario: Week and day items show their local time
  it("lists a day item with its local time, type and status", () => {
    process.env.TZ = "America/Sao_Paulo";
    withItems([blogPost]);
    renderPage("?view=day&date=2026-10-21");
    const item = screen.getByRole("listitem");
    expect(within(item).getByText("10:00 PM")).toBeInTheDocument();
    expect(within(item).getByText("Evening post")).toBeInTheDocument();
    expect(within(item).getByText("carousel")).toBeInTheDocument();
    expect(within(item).getByText("approved")).toBeInTheDocument();
  });

  // Scenario: A date-only item is listed as all day
  it("lists a date-only item as all day", () => {
    withItems([{ ...blogPost, event_date: "2026-10-21", phase_status: "x" }]);
    renderPage("?view=day&date=2026-10-21");
    const item = screen.getByRole("listitem");
    expect(within(item).getByText("All day")).toBeInTheDocument();
    expect(within(item).queryByText("approved")).not.toBeInTheDocument();
  });

  it("lists a week item under its day", () => {
    withItems([{ ...blogPost, event_date: "2026-10-23" }]);
    renderPage("?view=week&date=2026-10-21");
    expect(screen.getByText("Evening post")).toBeInTheDocument();
  });

  // Scenario: An empty day says nothing is scheduled
  it("says when the day has nothing scheduled", () => {
    renderPage("?view=day&date=2026-10-21");
    expect(
      screen.getByText("Nothing scheduled for this day"),
    ).toBeInTheDocument();
  });

  // Scenario: Schedule Post opens a dialog listing the approved blog posts
  it("opens the Schedule Post dialog from the header", async () => {
    const user = userEvent.setup();
    renderPage("");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Schedule Post/ }));
    expect(
      screen.getByRole("dialog", { name: "Schedule a blog post" }),
    ).toBeInTheDocument();
  });

  // Scenario: Keyboard focus stays in the dialog
  it("returns focus to Schedule Post when the dialog closes", async () => {
    const user = userEvent.setup();
    renderPage("");
    const trigger = screen.getByRole("button", { name: /Schedule Post/ });
    await user.click(trigger);
    expect(screen.getByRole("dialog")).toContainElement(
      document.activeElement as HTMLElement,
    );
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
