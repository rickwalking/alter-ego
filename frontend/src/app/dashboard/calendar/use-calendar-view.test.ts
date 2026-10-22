/**
 * Scenarios: tests/features/calendar-week-day-views.feature and
 * tests/features/calendar-month-navigation.feature.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

const nav = vi.hoisted(() => {
  const state = {
    search: "",
    history: [] as string[],
    replace: vi.fn((href: string) => {
      state.search = href.includes("?") ? href.slice(href.indexOf("?")) : "";
    }),
    push: vi.fn((href: string) => {
      state.history.push(state.search);
      state.replace(href);
    }),
    back: (): void => {
      state.search = state.history.pop() ?? "";
    },
  };
  return state;
});

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard/calendar",
  useRouter: () => ({ replace: nav.replace, push: nav.push }),
  useSearchParams: () => new URLSearchParams(nav.search),
}));

import { useCalendarView } from "./use-calendar-view";

const OCT_21 = new Date(2026, 9, 21);

function renderView(search: string, today: Date | null = OCT_21) {
  nav.search = search;
  const hook = renderHook(() => useCalendarView(today));
  const run = (action: () => void): void => {
    act(action);
    hook.rerender();
  };
  return { ...hook, run };
}

describe("useCalendarView", () => {
  beforeEach(() => {
    nav.replace.mockClear();
    nav.push.mockClear();
    nav.history = [];
  });

  // Scenario: Calendar opens on the current month
  it("opens on the current month by default", () => {
    const { result } = renderView("");
    expect(result.current.view).toBe("month");
    expect(result.current.title).toBe("October 2026");
  });

  // Scenario: The server render highlights no day
  it("has no focus and no title while today is unknown", () => {
    const { result } = renderView("?view=week&date=2026-10-21", null);
    expect(result.current.focus).toBeNull();
    expect(result.current.title).toBe("");
    result.current.goNext();
    expect(nav.replace).not.toHaveBeenCalled();
    expect(nav.push).not.toHaveBeenCalled();
  });

  // Scenario: The calendar opens on the viewer's local month at a month boundary
  it("opens on the local month on the last evening of a month", () => {
    const { result } = renderView("", new Date(2026, 9, 31, 21, 30));
    expect(result.current.title).toBe("October 2026");
  });

  // Scenario: Today moves on at local midnight while the page stays open
  it("follows today into the next month when no date is pinned", () => {
    nav.search = "";
    const { result, rerender } = renderHook(
      ({ today }: { today: Date }) => useCalendarView(today),
      { initialProps: { today: new Date(2026, 9, 31) } },
    );
    rerender({ today: new Date(2026, 10, 1) });
    expect(result.current.title).toBe("November 2026");
  });

  // Scenario: Month navigation is relative to the local month
  it("steps from the local month", () => {
    const { result, run } = renderView("", new Date(2026, 9, 31, 22, 0));
    run(() => result.current.goNext());
    expect(nav.search).toBe("?date=2026-11-01");
  });

  // Scenario: Switching to the week view shows the focused week
  it("switches to the week of today without putting today in the URL", () => {
    const { result, run } = renderView("");
    run(() => result.current.setView("week"));
    expect(nav.push).toHaveBeenLastCalledWith("/dashboard/calendar?view=week", {
      scroll: false,
    });
    expect(result.current.view).toBe("week");
    expect(result.current.title).toMatch(/^Oct 18\s–\s24, 2026$/);
  });

  // Scenario: Switching to the day view shows the focused day
  it("switches to the day view of today", () => {
    const { result, run } = renderView("");
    run(() => result.current.setView("day"));
    expect(nav.search).toBe("?view=day");
    expect(result.current.title).toBe("Wednesday, October 21, 2026");
  });

  // Scenario: The view and date are restored from the URL
  it("restores the view and the date from the URL", () => {
    const { result } = renderView("?view=day&date=2026-10-30");
    expect(result.current.view).toBe("day");
    expect(result.current.title).toBe("Friday, October 30, 2026");
  });

  it("keeps the URL date when the view changes", () => {
    const { result, run } = renderView("?view=day&date=2026-10-30");
    run(() => result.current.setView("week"));
    expect(nav.search).toBe("?view=week&date=2026-10-30");
  });

  it("drops the view param when switching back to the month", () => {
    const { result, run } = renderView("?view=week");
    run(() => result.current.setView("month"));
    expect(nav.push).toHaveBeenLastCalledWith("/dashboard/calendar", {
      scroll: false,
    });
  });

  // Scenario: Previous and next move by one week in the week view
  it("steps a week at a time in the week view", () => {
    const { result, run } = renderView("?view=week&date=2026-10-21");
    run(() => result.current.goNext());
    expect(nav.search).toBe("?view=week&date=2026-10-28");
    run(() => result.current.goPrev());
    expect(nav.search).toBe("?view=week&date=2026-10-21");
  });

  // Scenario: Previous and next move by one day in the day view
  it("steps a day at a time in the day view", () => {
    const { result, run } = renderView("?view=day&date=2026-10-21");
    run(() => result.current.goNext());
    expect(nav.search).toBe("?view=day&date=2026-10-22");
    run(() => result.current.goPrev());
    expect(nav.search).toBe("?view=day&date=2026-10-21");
  });

  // Scenario: Navigating to the previous month
  it("steps a month at a time in the month view", () => {
    const { result, run } = renderView("");
    run(() => result.current.goNext());
    expect(result.current.title).toBe("November 2026");
    run(() => result.current.goPrev());
    run(() => result.current.goPrev());
    expect(result.current.title).toBe("September 2026");
  });

  // Scenario: Today returns to the current day and drops the date from the URL
  it("returns to today and drops the date param", () => {
    const { result, run } = renderView("?view=week&date=2026-12-02");
    run(() => result.current.goToday());
    expect(nav.search).toBe("?view=week");
    expect(result.current.title).toMatch(/^Oct 18\s–\s24, 2026$/);
  });

  // Scenario: Returning to the current month
  it("returns to the current month from another month", () => {
    const { result, run } = renderView("?date=2027-03-01");
    expect(result.current.title).toBe("March 2027");
    run(() => result.current.goToday());
    expect(result.current.title).toBe("October 2026");
  });

  // Scenario: A week day header opens that day in the day view
  it("opens a given day in the day view", () => {
    const { result, run } = renderView("?view=week&date=2026-10-21");
    run(() => result.current.openDay(new Date(2026, 9, 22)));
    expect(nav.search).toBe("?view=day&date=2026-10-22");
  });

  it("keeps the same focus object between renders of the same URL", () => {
    const { result, rerender } = renderView("?view=day&date=2026-10-21");
    const first = result.current.focus;
    rerender();
    expect(result.current.focus).toBe(first);
  });

  // Scenario: Back returns to the previous view
  it("pushes view changes and day opens so Back restores the previous view", () => {
    const { result, run, rerender } = renderView("?view=week&date=2026-10-21");
    run(() => result.current.openDay(new Date(2026, 9, 22)));
    expect(result.current.view).toBe("day");
    nav.back();
    rerender();
    expect(result.current.view).toBe("week");
    expect(result.current.title).toMatch(/^Oct 18\s–\s24, 2026$/);
  });

  it("replaces history on prev, next and today so Back skips them", () => {
    const { result, run } = renderView("?view=week&date=2026-10-21");
    run(() => result.current.goNext());
    run(() => result.current.goPrev());
    run(() => result.current.goToday());
    expect(nav.push).not.toHaveBeenCalled();
    expect(nav.replace).toHaveBeenCalledTimes(3);
  });
});
