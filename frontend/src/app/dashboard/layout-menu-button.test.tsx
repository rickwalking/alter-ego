/**
 * Gherkin: tests/features/chat-shell-mobile.feature
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { DASHBOARD_MENU_BUTTON_ATTRIBUTE } from "@/constants/a11y";

vi.mock("@/components/organisms/neon-sidebar", () => ({
  NeonSidebar: () => null,
}));

import DashboardLayout from "./layout";

describe("DashboardLayout menu button", () => {
  /** Scenario: The mobile conversation drawer is opaque and above the menu button */
  it("marks the menu button so the chat drawer can take it out of reach", () => {
    render(
      <DashboardLayout>
        <p>page</p>
      </DashboardLayout>,
    );
    const marked = document.querySelector(
      `[${DASHBOARD_MENU_BUTTON_ATTRIBUTE}]`,
    );
    expect(marked).toBe(screen.getByRole("button", { name: /open menu/i }));
  });
});
