import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DashboardLayout from "./layout";

vi.mock("@/components/organisms/neon-sidebar", () => ({
  NeonSidebar: () => <nav aria-label="sidebar" />,
}));
vi.mock("@/components/layout/password-change-gate", () => ({
  PasswordChangeGate: ({ children }: { children: React.ReactNode }) => children,
}));

describe("dashboard mobile menu button", () => {
  // Scenario: The mobile menu button label comes from the translations
  it("is labelled from the translations when closed and open", () => {
    render(
      <DashboardLayout>
        <p>page</p>
      </DashboardLayout>,
    );
    const toggle = screen.getByRole("button", { name: "Open menu" });
    fireEvent.click(toggle);
    expect(toggle).toHaveAccessibleName("Close menu");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });
});
