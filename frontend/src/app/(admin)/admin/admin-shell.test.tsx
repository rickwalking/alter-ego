/**
 * Gherkin: tests/features/users-area-polish-ae0514.feature
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/admin/users",
}));

const auth = vi.hoisted(() => ({ isAdmin: true }));

vi.mock("@/modules/identity", () => ({
  useAuth: () => ({
    user: {
      id: "user-1",
      email: "user@example.com",
      full_name: "Some User",
      role: auth.isAdmin ? "admin" : "editor",
    },
    isLoading: false,
    isAdmin: auth.isAdmin,
    isEditor: !auth.isAdmin,
    logout: vi.fn(),
  }),
}));

import AdminLayout from "./layout";

function renderShell(): void {
  render(
    <AdminLayout>
      <h1>Users</h1>
    </AdminLayout>,
  );
}

afterEach(() => {
  auth.isAdmin = true;
});

describe("admin shell", () => {
  // Scenario: A non-admin does not see the Users link
  it("hides the Users link from a non-admin", () => {
    auth.isAdmin = false;
    renderShell();
    expect(
      screen.queryByRole("link", { name: /Users/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Dashboard/ })).toBeInTheDocument();
  });

  // Scenario: The admin shell has the PT/EN switch
  it("shows the EN | PT language switch in the sidebar", () => {
    renderShell();
    const switcher = screen.getByTestId("sidebar-language-switcher");
    expect(switcher).toHaveTextContent("EN");
    expect(switcher).toHaveTextContent("PT");
  });

  // Scenario: The admin sidebar is a drawer on a phone
  it("opens the sidebar drawer from the menu button and closes it on Escape", async () => {
    const user = userEvent.setup();
    renderShell();
    const menu = screen.getByRole("button", { name: "Open menu" });
    const sidebar = screen.getByRole("complementary");
    expect(menu).toHaveAttribute("aria-controls", sidebar.id);
    expect(sidebar).toHaveClass("-translate-x-full");

    await user.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    expect(sidebar).toHaveClass("translate-x-0");

    await user.keyboard("{Escape}");
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(sidebar).toHaveClass("-translate-x-full");
  });

  // Scenario: The admin sidebar is a drawer on a phone
  it("closes the drawer when the overlay is tapped", async () => {
    const user = userEvent.setup();
    renderShell();

    await user.click(screen.getByRole("button", { name: "Open menu" }));
    const overlays = screen.getAllByRole("button", { name: "Close menu" });
    await user.click(overlays[overlays.length - 1]!);

    expect(screen.getByRole("button", { name: "Open menu" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  // Scenario: The admin sidebar is a drawer on a phone
  it("links back to the dashboard and to the users page", () => {
    renderShell();
    expect(screen.getByRole("link", { name: /Users/ })).toHaveAttribute(
      "href",
      "/admin/users",
    );
    expect(screen.getByRole("link", { name: /Dashboard/ })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("main")).toContainElement(
      screen.getByRole("heading", { name: "Users" }),
    );
  });
});
