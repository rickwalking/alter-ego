/**
 * Gherkin: tests/features/chat-shell-mobile.feature
 */
import { afterEach, describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";

import { DASHBOARD_MENU_BUTTON_ATTRIBUTE } from "@/constants/a11y";
import { useMenuButtonHidden } from "./use-menu-button-hidden";

function mountMenuButton(): HTMLButtonElement {
  const button = document.createElement("button");
  button.setAttribute(DASHBOARD_MENU_BUTTON_ATTRIBUTE, "");
  document.body.append(button);
  return button;
}

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
});
