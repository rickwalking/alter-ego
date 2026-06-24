import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonSidebar } from "@/components/organisms/neon-sidebar";
import { DASHBOARD_SIDEBAR_SECTIONS } from "@/components/organisms/constants";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/modules/identity", () => ({
  useAuth: () => ({
    user: {
      id: "user-1",
      email: "editor@example.com",
      full_name: "Test User",
      role: "editor",
    },
    isLoading: false,
    isAdmin: false,
    isEditor: true,
    logout: vi.fn(),
  }),
}));

describe("NeonSidebar", () => {
  it("renders navigation links from sections", () => {
    render(<NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} />);
    expect(screen.getByText("Alter Ego")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /dashboard/i }),
    ).toBeInTheDocument();
  });

  it("hides user footer when showUserFooter is false", () => {
    render(
      <NeonSidebar
        sections={DASHBOARD_SIDEBAR_SECTIONS}
        showUserFooter={false}
      />,
    );
    expect(screen.queryByText("Test User")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /logout/i }),
    ).not.toBeInTheDocument();
  });

  it("shows authenticated user footer when showUserFooter is true", () => {
    render(
      <NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} showUserFooter />,
    );
    expect(screen.getByText("Test User")).toBeInTheDocument();
    expect(screen.getByText("editor@example.com")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /logout/i })).toBeInTheDocument();
  });

  // Feature: responsive-dashboard-shell.feature — drawer on mobile / rail on desktop.
  it("is translated off-canvas when closed and wired for the rail at lg", () => {
    const { container } = render(
      <NeonSidebar
        sections={DASHBOARD_SIDEBAR_SECTIONS}
        open={false}
        id="dashboard-sidebar"
      />,
    );
    const aside = container.querySelector("aside");
    expect(aside).toHaveAttribute("id", "dashboard-sidebar");
    expect(aside?.className).toContain("-translate-x-full");
    expect(aside?.className).toContain("lg:translate-x-0");
    expect(aside?.className).toContain("w-[240px]");
  });

  it("slides into view when open", () => {
    const { container } = render(
      <NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} open />,
    );
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("translate-x-0");
    expect(aside?.className).not.toContain("-translate-x-full");
  });
});
