import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MobileNav } from "./mobile-nav";

const translate = (key: string): string => `nav.${key}`;
vi.mock("next-intl", () => ({
  useTranslations: () => translate,
}));

vi.mock("@/modules/identity", () => ({
  useAuth: () => ({ user: null, isEditor: false, isAdmin: false }),
}));

describe("MobileNav", () => {
  it("labels the menu button from the translations", () => {
    // Scenario: The mobile menu button label comes from the translations
    render(<MobileNav />);
    expect(
      screen.getByRole("button", { name: "nav.openMenu" }),
    ).toBeInTheDocument();
  });
});
