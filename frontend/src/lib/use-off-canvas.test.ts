/**
 * AE-0273 — useOffCanvas. Feature: responsive-dashboard-shell.feature
 * Scenarios: Escape closes the drawer; Navigating closes the drawer.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

let mockPathname = "/dashboard";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

import { useOffCanvas } from "./use-off-canvas";

afterEach(() => {
  mockPathname = "/dashboard";
});

describe("useOffCanvas", () => {
  it("starts closed and toggles open", () => {
    const { result } = renderHook(() => useOffCanvas());
    expect(result.current.open).toBe(false);
    act(() => result.current.toggle());
    expect(result.current.open).toBe(true);
    act(() => result.current.toggle());
    expect(result.current.open).toBe(false);
  });

  it("close() sets open false", () => {
    const { result } = renderHook(() => useOffCanvas());
    act(() => result.current.setOpen(true));
    expect(result.current.open).toBe(true);
    act(() => result.current.close());
    expect(result.current.open).toBe(false);
  });

  it("closes on Escape", () => {
    const { result } = renderHook(() => useOffCanvas());
    act(() => result.current.setOpen(true));
    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(result.current.open).toBe(false);
  });

  it("closes when the route changes", () => {
    const { result, rerender } = renderHook(() => useOffCanvas());
    act(() => result.current.setOpen(true));
    expect(result.current.open).toBe(true);
    mockPathname = "/dashboard/create";
    rerender();
    expect(result.current.open).toBe(false);
  });
});
