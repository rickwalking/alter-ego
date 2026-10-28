import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DASHBOARD_SIDEBAR_SECTIONS } from "@/components/organisms/constants";
import { NeonSidebar } from "@/components/organisms/neon-sidebar";

const pathname = vi.hoisted(() => ({ value: "/dashboard" }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.value }));
vi.mock("@/modules/identity", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "u@example.com",
      full_name: "U",
      role: "editor",
    },
    isLoading: false,
    isAdmin: false,
    isEditor: true,
    logout: vi.fn(),
  }),
}));

function workflowItem(): HTMLElement {
  const navigation = screen.getByRole("navigation");
  return (
    within(navigation)
      .getAllByRole("link")
      .find((link) => link.getAttribute("href") === "/dashboard/workflow") ??
    (() => {
      throw new Error("workflow link missing");
    })()
  );
}

describe("sidebar active item", () => {
  /** Scenario: The carousel workspace marks the board active */
  it("marks Workflow Board active on a carousel workspace page", () => {
    pathname.value = "/dashboard/create/123e4567";
    render(<NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} />);
    expect(workflowItem()).toHaveAttribute("aria-current", "page");
  });

  /** Scenario: The carousel workspace marks the board active */
  it("does not mark Workflow Board active on the create wizard page", () => {
    pathname.value = "/dashboard/create";
    render(<NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} />);
    expect(workflowItem()).not.toHaveAttribute("aria-current", "page");
  });

  it("does not mark Workflow Board active on the board page itself twice", () => {
    pathname.value = "/dashboard/workflow";
    render(<NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} />);
    expect(workflowItem()).toHaveAttribute("aria-current", "page");
  });
});
