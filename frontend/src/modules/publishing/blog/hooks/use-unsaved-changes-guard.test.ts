import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useUnsavedChangesGuard } from "./use-unsaved-changes-guard";

// Scenario: Leaving with unsaved changes is guarded
//   (tests/features/blog_editor_ae0424.feature)

function clickLink(target?: string): MouseEvent {
  const link = document.createElement("a");
  link.href = "/dashboard";
  if (target) {
    link.target = target;
  }
  document.body.appendChild(link);
  const event = new MouseEvent("click", { bubbles: true, cancelable: true });
  link.dispatchEvent(event);
  link.remove();
  return event;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useUnsavedChangesGuard", () => {
  it("blocks tab close while dirty", () => {
    renderHook(() => useUnsavedChangesGuard(true, "Leave?"));
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
  });

  it("asks before following an in-app link and cancels on 'no'", () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderHook(() => useUnsavedChangesGuard(true, "Leave?"));
    expect(clickLink().defaultPrevented).toBe(true);
    expect(confirm).toHaveBeenCalledWith("Leave?");
    confirm.mockReturnValue(true);
    expect(clickLink().defaultPrevented).toBe(false);
  });

  it("ignores new-tab links and clean drafts", () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const { rerender } = renderHook(
      ({ dirty }) => useUnsavedChangesGuard(dirty, "Leave?"),
      {
        initialProps: { dirty: true },
      },
    );
    expect(clickLink("_blank").defaultPrevented).toBe(false);
    rerender({ dirty: false });
    expect(clickLink().defaultPrevented).toBe(false);
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
    expect(confirm).not.toHaveBeenCalled();
  });

  it("confirmLeave asks only when dirty", () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const clean = renderHook(() => useUnsavedChangesGuard(false, "Leave?"));
    expect(clean.result.current.confirmLeave()).toBe(true);
    const dirty = renderHook(() => useUnsavedChangesGuard(true, "Leave?"));
    expect(dirty.result.current.confirmLeave()).toBe(false);
    expect(confirm).toHaveBeenCalledTimes(1);
  });
});
