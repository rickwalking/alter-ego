import { act, renderHook } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useClientToday } from "./use-client-today";

function TodayProbe(): React.ReactElement {
  const today = useClientToday();
  return <span>{today ? today.toDateString() : "unknown"}</span>;
}

describe("useClientToday", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  // Scenario: The server render highlights no day
  it("is unknown during the server render", () => {
    expect(renderToString(<TodayProbe />)).toContain("unknown");
  });

  // Scenario: Today is the viewer's local date after the page loads
  it("is the local calendar day in the browser", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 21, 21, 30));
    const { result } = renderHook(() => useClientToday());
    expect(result.current).toEqual(new Date(2026, 9, 21));
  });

  // Scenario: Today moves on at local midnight while the page stays open
  it("moves to the next day after local midnight", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 21, 23, 59, 30));
    const { result } = renderHook(() => useClientToday());
    expect(result.current).toEqual(new Date(2026, 9, 21));
    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    expect(result.current).toEqual(new Date(2026, 9, 22));
  });
});
