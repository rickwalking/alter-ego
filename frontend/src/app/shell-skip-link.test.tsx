import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AdminLayout from "@/app/(admin)/admin/layout";
import DashboardLayout from "@/app/dashboard/layout";

vi.mock("@/components/admin/admin-sidebar", () => ({
  AdminSidebar: () => <nav aria-label="admin" />,
}));
vi.mock("@/components/organisms/neon-sidebar", () => ({
  NeonSidebar: () => <nav aria-label="sidebar" />,
}));

describe("shell skip links", () => {
  // Scenario: Keyboard users can skip to the main content
  it.each([
    ["admin", AdminLayout],
    ["dashboard", DashboardLayout],
  ])("is the first focusable element of the %s shell", (_, Layout) => {
    const { container } = render(
      <Layout>
        <p>page</p>
      </Layout>,
    );
    const first = container.querySelector("a, button");
    expect(first).toHaveTextContent("Skip to content");
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "main-content");
    expect(main).toHaveAttribute("tabindex", "-1");
  });
});
