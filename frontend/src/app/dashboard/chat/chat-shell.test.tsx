/**
 * Gherkin: tests/features/chat-shell-mobile.feature
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { DASHBOARD_CHAT_BG_DEEP } from "@/modules/editorial-operations";
import { ChatComposer } from "./chat-composer";
import { ChatHeader } from "./chat-header";
import { ChatMessageList } from "./chat-message-list";
import { ChatSidebar } from "./chat-sidebar";

describe("chat shell", () => {
  /** Scenario: The public chat has the site header */
  it("drops the menu-button gutter in the public shell and keeps New chat on one line", () => {
    const { container } = render(
      <ChatHeader onNewChat={vi.fn()} publicShell />,
    );
    const bar = container.firstElementChild!;
    expect(bar).not.toHaveClass("pl-16");
    expect(screen.queryByRole("banner")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New chat" })).toHaveClass(
      "whitespace-nowrap",
    );
  });

  it("keeps the gutter for the dashboard menu button", () => {
    render(<ChatHeader onNewChat={vi.fn()} />);
    expect(screen.getByRole("banner")).toHaveClass("pl-16");
  });

  /** Scenario: No fake notifications */
  it("has no notifications bell", () => {
    render(<ChatHeader onNewChat={vi.fn()} publicShell />);
    expect(
      screen.queryByRole("button", { name: /notifications/i }),
    ).not.toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });

  /** Scenario: The chat fits the mobile viewport above the browser bars and home indicator */
  it("uses a 16px message box and pads the composer for the home indicator", () => {
    const { container } = render(
      <ChatComposer value="" onChange={vi.fn()} onSend={vi.fn()} />,
    );
    expect(screen.getByRole("textbox").style.fontSize).toBe("16px");
    const bar = container.firstElementChild as HTMLElement;
    expect(bar.getAttribute("style")).toContain("safe-area-inset-bottom");
  });

  /** Scenario: Touch targets are at least 44 pixels */
  it("makes Send and New chat at least 44px", () => {
    render(
      <>
        <ChatHeader onNewChat={vi.fn()} publicShell />
        <ChatComposer value="hi" onChange={vi.fn()} onSend={vi.fn()} />
      </>,
    );
    const send = screen.getByRole("button", { name: "Send message" });
    expect(send.style.width).toBe("44px");
    expect(send.style.height).toBe("44px");
    expect(screen.getByRole("button", { name: "New chat" })).toHaveClass(
      "min-h-11",
    );
  });

  /** Scenario: The mobile conversation drawer is opaque and above the menu button */
  it("draws the drawer solid and above the z-50 menu button", () => {
    render(
      <ChatSidebar
        conversations={[]}
        activeConv=""
        onSelectConversation={vi.fn()}
        open
        id="drawer"
      />,
    );
    const drawer = document.getElementById("drawer")!;
    expect(drawer).toHaveClass("z-[60]");
    expect(drawer.style.background).toBe(toCssColor(DASHBOARD_CHAT_BG_DEEP));
    expect(drawer.style.background).not.toMatch(/rgba\(.*0\.\d+\)/);
  });

  /** Scenario: Visitors' messages do not carry the owner's initials */
  it("shows a neutral icon, not PM, on the visitor's messages", () => {
    render(
      <ChatMessageList
        messages={[{ role: "user", text: "hi", time: "10:00" }]}
      />,
    );
    expect(screen.queryByText("PM")).not.toBeInTheDocument();
    expect(screen.getByTestId("chat-user-avatar")).toBeInTheDocument();
  });
});

/** The color as jsdom normalizes it in a style attribute. */
function toCssColor(color: string): string {
  const probe = document.createElement("div");
  probe.style.background = color;
  return probe.style.background;
}
