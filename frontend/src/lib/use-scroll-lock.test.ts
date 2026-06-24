/**
 * AE-0273 — useScrollLock. Feature: responsive-dashboard-shell.feature
 * Scenario: Opening the drawer traps focus and locks body scroll.
 */
import { afterEach, describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";

import { useScrollLock } from "./use-scroll-lock";

afterEach(() => {
  document.body.style.overflow = "";
  document.body.style.overscrollBehavior = "";
});

describe("useScrollLock", () => {
  it("locks body scroll while active", () => {
    renderHook(() => useScrollLock(true));
    expect(document.body.style.overflow).toBe("hidden");
    expect(document.body.style.overscrollBehavior).toBe("contain");
  });

  it("does not lock when inactive", () => {
    renderHook(() => useScrollLock(false));
    expect(document.body.style.overflow).toBe("");
  });

  it("restores the previous values on unmount", () => {
    document.body.style.overflow = "auto";
    const { unmount } = renderHook(() => useScrollLock(true));
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).toBe("auto");
  });

  it("releases the lock when toggled inactive", () => {
    const { rerender } = renderHook(({ active }) => useScrollLock(active), {
      initialProps: { active: true },
    });
    expect(document.body.style.overflow).toBe("hidden");
    rerender({ active: false });
    expect(document.body.style.overflow).toBe("");
  });
});
