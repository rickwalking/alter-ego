/**
 * Gherkin: tests/features/change-own-password-ae0511.feature
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SidebarUserFooter } from "./neon-sidebar-user-footer";

const USER = {
  id: "u1",
  email: "editor@example.com",
  full_name: "Editor",
  role: "editor",
  must_change_password: false,
};

describe("SidebarUserFooter", () => {
  // Scenario: The sidebar links to the change-password page
  it("links to the change-password page next to logout", () => {
    render(<SidebarUserFooter user={USER} onLogout={vi.fn()} />);

    const link = screen.getByRole("link", { name: "Change password" });
    expect(link).toHaveAttribute("href", "/dashboard/account/password");
    expect(link).toHaveClass("[@media(pointer:coarse)]:h-11");
    expect(screen.getByRole("button", { name: "Logout" })).toBeInTheDocument();
  });
});
