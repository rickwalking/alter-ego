/**
 * Gherkin: tests/features/chat-errors-ui.feature
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { CHAT_ERROR_KIND, type ChatErrorKind } from "@/modules/conversation";
import { ChatErrorBanner } from "./chat-error-banner";
import type { ChatErrorBannerProps } from "./types";

function renderBanner(
  props: Partial<ChatErrorBannerProps> & { kind: ChatErrorKind },
) {
  const onRetry = vi.fn();
  render(<ChatErrorBanner onRetry={onRetry} {...props} />);
  return { onRetry };
}

describe("ChatErrorBanner", () => {
  /** Scenario: Each failure shows a plain, localized message */
  it.each([
    ["offline", /you seem to be offline/i],
    ["generic", /something went wrong/i],
  ] as const)("explains %s in plain words with a Retry", (kind, text) => {
    const { onRetry } = renderBanner({ kind, canRetry: true });

    expect(screen.getByRole("alert")).toHaveTextContent(text);
    expect(screen.getByRole("alert")).not.toHaveTextContent(/HTTP|fetch/);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  /** Scenario: Each failure shows a plain, localized message */
  it("has every message in English and Portuguese", () => {
    for (const kind of Object.values(CHAT_ERROR_KIND)) {
      expect(en.chat.errors[kind]).toBeTruthy();
      expect(pt.chat.errors[kind]).toBeTruthy();
      expect(pt.chat.errors[kind]).not.toBe(en.chat.errors[kind]);
    }
    expect(pt.chat.errors.retry).toBe("Tentar de novo");
  });

  /** Scenario: An over-long message explains the limit instead of "HTTP 422" */
  it("states the limit and offers no Retry for a too-long message", () => {
    renderBanner({ kind: "tooLong" });
    expect(screen.getByRole("alert")).toHaveTextContent(
      /under 2000 characters/,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  /** Scenario: A signed-in user whose session expired is told to sign in again */
  it("offers Sign in back to the chat when the session expired", () => {
    renderBanner({
      kind: "sessionExpired",
      loginRedirect: "/dashboard/chat",
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/session expired/i);
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/login?redirect=%2Fdashboard%2Fchat",
    );
  });

  /** Scenario: An expired or missing conversation offers a new chat */
  it("tells a visitor the conversation is gone and offers a new chat", () => {
    const onNewChat = vi.fn();
    renderBanner({ kind: "notFound", onNewChat });
    expect(screen.getByRole("alert")).toHaveTextContent(/no longer available/);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start a new chat" }));
    expect(onNewChat).toHaveBeenCalledOnce();
  });

  /** Scenario: A full conversation offers a new chat instead of a retry */
  it("offers a new chat, not a retry, when the conversation is full", () => {
    const onNewChat = vi.fn();
    renderBanner({ kind: "limit", onNewChat });
    expect(screen.getByRole("alert")).toHaveTextContent(/too many messages/i);
    expect(
      screen.queryByRole("button", { name: "Try again" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start a new chat" }));
    expect(onNewChat).toHaveBeenCalledOnce();
  });

  /** Scenario: Retry is offered only when nothing was saved yet */
  it("offers only a new chat after a failure once the answer had started", () => {
    renderBanner({ kind: "generic", canRetry: false, onNewChat: vi.fn() });
    expect(
      screen.queryByRole("button", { name: "Try again" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Start a new chat" }),
    ).toBeInTheDocument();
  });
});
