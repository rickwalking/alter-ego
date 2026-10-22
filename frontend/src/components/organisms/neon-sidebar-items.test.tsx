import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { DASHBOARD_SIDEBAR_SECTIONS } from "@/components/organisms/constants";
import { NeonSidebar } from "@/components/organisms/neon-sidebar";

const auth = vi.hoisted(() => ({ role: "editor" }));
vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard" }));
vi.mock("@/modules/identity", () => ({
  useAuth: () => ({
    user: { id: "u1", email: "u@example.com", full_name: "U", role: auth.role },
    isLoading: false,
    isAdmin: auth.role === "admin",
    isEditor: true,
    logout: vi.fn(),
  }),
}));

function hrefs(): (string | null)[] {
  return within(screen.getByRole("navigation"))
    .getAllByRole("link")
    .map((link) => link.getAttribute("href"));
}

describe("dashboard sidebar items", () => {
  // Scenario: The sidebar links Palettes, Knowledge and Analytics
  it("links palettes, knowledge and analytics", () => {
    auth.role = "editor";
    render(<NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} />);
    expect(hrefs()).toEqual(
      expect.arrayContaining([
        "/dashboard/palettes",
        "/dashboard/knowledge",
        "/dashboard/analytics",
      ]),
    );
  });

  // Scenario: Only admins see the user administration link
  it.each([
    ["admin", true],
    ["editor", false],
  ])("shows the users link to a %s: %s", (role, shown) => {
    auth.role = role;
    render(<NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} />);
    expect(hrefs().includes("/admin/users")).toBe(shown);
  });

  // Scenario: Chat shows no invented unread badge
  it("shows no badge on chat", () => {
    auth.role = "admin";
    render(<NeonSidebar sections={DASHBOARD_SIDEBAR_SECTIONS} />);
    const chat = screen.getByRole("link", { name: "Chat" });
    expect(chat).toHaveTextContent(/^Chat$/);
    for (const section of DASHBOARD_SIDEBAR_SECTIONS) {
      for (const item of section.items) {
        expect(item).not.toHaveProperty("badge");
      }
    }
  });

  // Scenario: Every sidebar label exists in both languages
  it("has every label in English and Portuguese", () => {
    const keys = DASHBOARD_SIDEBAR_SECTIONS.flatMap((section) => [
      section.sectionKey,
      ...section.items.map((item) => item.labelKey),
    ]);
    for (const key of keys) {
      expect(en.common.sidebar).toHaveProperty(key);
      expect(pt.common.sidebar).toHaveProperty(key);
    }
  });
});
