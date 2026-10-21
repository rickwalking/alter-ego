import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PublicHeaderNav } from "@/components/layout/public-header";

vi.mock("@/components/language-switcher", () => ({
  LanguageSwitcher: () => <div data-testid="language-switcher" />,
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const MESSAGES: Record<string, string> = {
  "nav.chat": "Chat",
  "nav.blog": "Blog",
  "nav.carousels": "Carousels",
  login: "Login",
};

function t(key: string): string {
  return MESSAGES[key] ?? key;
}

// Feature: Landing page truth, links and public header (AE-0443)
describe("PublicHeaderNav", () => {
  // Scenario: The public header links to Carousels next to Blog
  it("puts the Carousels link after Blog and points it at /carousels", () => {
    render(<PublicHeaderNav t={t} locale="en" />);

    const nav = screen.getByRole("navigation");
    const labels = within(nav)
      .getAllByRole("link")
      .map((link) => link.textContent);

    expect(labels).toEqual(["Chat", "Blog", "Carousels"]);
    expect(screen.getByRole("link", { name: "Carousels" })).toHaveAttribute(
      "href",
      "/carousels",
    );
  });

  // Scenario: The public header does not offer Login
  it("does not render a Login link", () => {
    render(<PublicHeaderNav t={t} locale="en" />);

    expect(
      screen.queryByRole("link", { name: "Login" }),
    ).not.toBeInTheDocument();
  });
});
