/**
 * AE-0273 — useFocusTrap. Feature: responsive-dashboard-shell.feature
 * Scenarios: focus is trapped inside the drawer; focus returns on close.
 */
import { describe, expect, it } from "vitest";
import { createRef } from "react";
import { render, renderHook } from "@testing-library/react";

import { useFocusTrap } from "./use-focus-trap";

function renderTrap(active: boolean): {
  ref: React.RefObject<HTMLDivElement | null>;
  first: HTMLButtonElement;
  last: HTMLButtonElement;
} {
  const ref = createRef<HTMLDivElement>();
  render(
    <div ref={ref}>
      <button type="button">first</button>
      <button type="button">last</button>
    </div>,
  );
  renderHook(() => useFocusTrap(ref, active));
  const buttons = ref.current!.querySelectorAll("button");
  return {
    ref,
    first: buttons[0] as HTMLButtonElement,
    last: buttons[1] as HTMLButtonElement,
  };
}

describe("useFocusTrap", () => {
  it("moves focus to the first focusable element when active", () => {
    const { first } = renderTrap(true);
    expect(document.activeElement).toBe(first);
  });

  it("does nothing when inactive", () => {
    const before = document.activeElement;
    renderTrap(false);
    expect(document.activeElement).toBe(before);
  });

  it("wraps focus from last to first on Tab", () => {
    const { ref, first, last } = renderTrap(true);
    last.focus();
    const event = new KeyboardEvent("keydown", {
      key: "Tab",
      bubbles: true,
      cancelable: true,
    });
    ref.current!.dispatchEvent(event);
    expect(document.activeElement).toBe(first);
  });

  it("wraps focus from first to last on Shift+Tab", () => {
    const { ref, first, last } = renderTrap(true);
    first.focus();
    const event = new KeyboardEvent("keydown", {
      key: "Tab",
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    });
    ref.current!.dispatchEvent(event);
    expect(document.activeElement).toBe(last);
  });

  it("returns focus to the prior element when deactivated", () => {
    const trigger = document.createElement("button");
    document.body.appendChild(trigger);
    trigger.focus();
    const ref = createRef<HTMLDivElement>();
    render(
      <div ref={ref}>
        <button type="button">inside</button>
      </div>,
    );
    const { rerender } = renderHook(({ active }) => useFocusTrap(ref, active), {
      initialProps: { active: true },
    });
    expect(document.activeElement).toBe(ref.current!.querySelector("button"));
    rerender({ active: false });
    expect(document.activeElement).toBe(trigger);
    trigger.remove();
  });
});
