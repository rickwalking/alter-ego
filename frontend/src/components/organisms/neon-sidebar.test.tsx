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

vi.mock("@/hooks/use-auth", () => ({
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
});
