/**
 * Gherkin: tests/features/chat-a11y-i18n.feature, tests/features/chat-shell-mobile.feature
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/components/layout/public-header", () => ({
  PublicHeader: () => <header data-testid="site-header" />,
}));

import { PUBLIC_CHAT_SHELL_STYLE } from "./chat-shell-style";
import PublicChatLayout, { viewport } from "./layout";

function renderLayout() {
  return render(
    <PublicChatLayout>
      <main id="main-content">chat</main>
    </PublicChatLayout>,
  );
}

describe("PublicChatLayout", () => {
  /** Scenario: The public chat has a main landmark and a skip link */
  it("starts with a skip link to the main content", () => {
    renderLayout();
    expect(
      screen.getByRole("link", { name: "Skip to content" }),
    ).toHaveAttribute("href", "#main-content");
  });

  /** Scenario: The public chat has the site header */
  it("renders the site header above the chat", () => {
    renderLayout();
    expect(screen.getByTestId("site-header")).toBeInTheDocument();
  });

  /** Scenario: The chat fits the mobile viewport above the browser bars and home indicator */
  it("fills the dynamic viewport and opts into safe-area insets", () => {
    const { container } = renderLayout();
    expect(container.firstElementChild).toHaveClass("h-dvh");
    expect(container.firstElementChild).not.toHaveClass("h-screen");
    expect(viewport).toEqual({
      width: "device-width",
      initialScale: 1,
      viewportFit: "cover",
    });
    expect(PUBLIC_CHAT_SHELL_STYLE.position).toBe("relative");
    expect(PUBLIC_CHAT_SHELL_STYLE.zIndex).toBe(1);
    expect(PUBLIC_CHAT_SHELL_STYLE.paddingLeft).toBe(
      "env(safe-area-inset-left)",
    );
    expect(PUBLIC_CHAT_SHELL_STYLE.paddingRight).toBe(
      "env(safe-area-inset-right)",
    );
  });
});
