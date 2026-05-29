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

describe("NeonSidebar", () => {
  it("renders navigation links from sections", () => {
    render(<NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} />);
    expect(screen.getByText("Alter Ego")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument();
  });
});
