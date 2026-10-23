/**
 * Gherkin: tests/features/chat-shell-mobile.feature
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";

import { DASHBOARD_MENU_BUTTON_ATTRIBUTE } from "@/constants/a11y";
const viewport = vi.hoisted(() => ({ narrow: true }));

vi.mock("@/lib/use-media-query", () => ({
  useMediaQuery: () => viewport.narrow,
}));

import { useMenuButtonHidden } from "./use-menu-button-hidden";

function mountMenuButton(): HTMLButtonElement {
  const button = document.createElement("button");
  button.setAttribute(DASHBOARD_MENU_BUTTON_ATTRIBUTE, "");
  document.body.append(button);
  return button;
}

beforeEach(() => {
  viewport.narrow = true;
});

afterEach(() => {
  document.body.innerHTML = "";
});

describe("useMenuButtonHidden", () => {
  /** Scenario: The mobile conversation drawer is opaque and above the menu button */
  it("hides the menu button and takes it out of reach while the drawer is open", () => {
    const button = mountMenuButton();
    const { rerender } = renderHook(({ open }) => useMenuButtonHidden(open), {
      initialProps: { open: true },
    });
    expect(button).toHaveAttribute("inert");
    expect(button).not.toBeVisible();

    rerender({ open: false });
    expect(button).not.toHaveAttribute("inert");
    expect(button).toBeVisible();
  });

  /** Scenario: The mobile conversation drawer is opaque and above the menu button */
  it("gives the menu button back when the chat unmounts", () => {
    const button = mountMenuButton();
    const { unmount } = renderHook(() => useMenuButtonHidden(true));
    unmount();
    expect(button).not.toHaveAttribute("inert");
    expect(button).toBeVisible();
  });

  /** Scenario: The mobile conversation drawer is opaque and above the menu button */
  it("leaves the menu button alone while the drawer is closed", () => {
    const button = mountMenuButton();
    renderHook(() => useMenuButtonHidden(false));
    expect(button).not.toHaveAttribute("inert");
    expect(button).toBeVisible();
  });

  /** Scenario: The mobile conversation drawer is opaque and above the menu button */
  it("gives the menu button back when the screen widens past the drawer breakpoint", () => {
    const button = mountMenuButton();
    const { rerender } = renderHook(() => useMenuButtonHidden(true));
    expect(button).toHaveAttribute("inert");

    viewport.narrow = false;
    rerender();

    expect(button).not.toHaveAttribute("inert");
    expect(button).toBeVisible();
  });

  /** Scenario: The mobile conversation drawer is opaque and above the menu button */
  it("never hides the menu button on a wide screen", () => {
    viewport.narrow = false;
    const button = mountMenuButton();
    renderHook(() => useMenuButtonHidden(true));
    expect(button).not.toHaveAttribute("inert");
    expect(button).toBeVisible();
  });
});
