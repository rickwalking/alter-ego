/**
 * AE-0273/0276: useMediaQuery — gates drawer scroll-lock/focus-trap to below a
 * breakpoint. Must be SSR/jsdom-safe (no throw when matchMedia is absent/partial).
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";

import { useMediaQuery } from "./use-media-query";

const originalMatchMedia = window.matchMedia;

afterEach(() => {
  window.matchMedia = originalMatchMedia;
});

describe("useMediaQuery", () => {
  it("returns false initially (SSR-safe default)", () => {
    const { result } = renderHook(() => useMediaQuery("(max-width: 767px)"));
    expect(result.current).toBe(false);
  });

  it("reflects a matching query after mount", () => {
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }) as unknown as typeof window.matchMedia;
    const { result } = renderHook(() => useMediaQuery("(max-width: 767px)"));
    expect(result.current).toBe(true);
  });

  it("does not throw when matchMedia returns undefined", () => {
    window.matchMedia = vi
      .fn()
      .mockReturnValue(undefined) as unknown as typeof window.matchMedia;
    expect(() =>
      renderHook(() => useMediaQuery("(max-width: 767px)")),
    ).not.toThrow();
  });
});
