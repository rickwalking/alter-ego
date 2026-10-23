/**
 * Gherkin: tests/features/chat-a11y-i18n.feature
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { ChatComposer } from "./chat-composer";
import { ChatHeader } from "./chat-header";
import { ChatMessageList } from "./chat-message-list";

function keyPaths(node: unknown, prefix = ""): string[] {
  if (typeof node !== "object" || node === null) return [prefix];
  return Object.entries(node).flatMap(([key, value]) =>
    keyPaths(value, prefix ? `${prefix}.${key}` : key),
  );
}

describe("chat accessibility", () => {
  /** Scenario: Replies are announced to screen readers once */
  it("is a labelled log that announces typing, then the finished reply", () => {
    const question = { role: "user" as const, text: "hi", time: "10:00" };
    const { rerender } = render(
      <ChatMessageList messages={[question]} isStreaming />,
    );
    expect(screen.getByRole("log", { name: "Conversation" })).toBeVisible();
    const live = document.querySelector('[aria-live="polite"]');
    expect(live).toHaveTextContent("Alter-Ego is typing…");

    rerender(
      <ChatMessageList
        messages={[
          question,
          { role: "assistant", text: "Hello there", time: "10:00" },
        ]}
      />,
    );
    expect(live).toHaveTextContent("Alter-Ego replied: Hello there");
  });

  /** Scenario: Replies are announced to screen readers once */
  it("announces nothing when another conversation's history loads", () => {
    const { rerender } = render(<ChatMessageList messages={[]} />);
    rerender(
      <ChatMessageList
        messages={[{ role: "assistant", text: "Old reply", time: "09:00" }]}
      />,
    );
    const live = document.querySelector('[aria-live="polite"]');
    expect(live).toBeEmptyDOMElement();
  });

  /** Scenario: Replies are announced to screen readers once */
  it("reads a finished reply without markdown and cut short", () => {
    const question = { role: "user" as const, text: "hi", time: "10:00" };
    const { rerender } = render(
      <ChatMessageList messages={[question]} isStreaming />,
    );
    rerender(
      <ChatMessageList
        messages={[
          question,
          {
            role: "assistant",
            text: `## **Bold** ${"x".repeat(400)}`,
            time: "10:00",
          },
        ]}
      />,
    );
    const text = document.querySelector('[aria-live="polite"]')!.textContent;
    expect(text).not.toMatch(/[#*]/);
    expect(text.endsWith("…")).toBe(true);
    expect(text.length).toBeLessThan(330);
  });

  /** Scenario: The message box has a label and a visible focus ring */
  it("labels the message box and keeps a focus outline", () => {
    render(<ChatComposer value="" onChange={vi.fn()} onSend={vi.fn()} />);
    const textarea = screen.getByRole("textbox", {
      name: "Message to the Alter-Ego",
    });
    expect(textarea.style.outline).toBe("");
    expect(textarea.className).toContain("focus-visible:outline");
  });

  /** Scenario: Focus stays in the message box after sending */
  it("keeps the message box enabled and focused while a reply streams", () => {
    const onSend = vi.fn();
    const { rerender } = render(
      <ChatComposer value="hello" onChange={vi.fn()} onSend={onSend} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    rerender(<ChatComposer value="" onChange={vi.fn()} onSend={onSend} busy />);

    const textarea = screen.getByRole("textbox");
    expect(onSend).toHaveBeenCalledOnce();
    expect(textarea).toBeEnabled();
    expect(textarea).toHaveFocus();
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });
});

describe("chat localization", () => {
  /** Scenario: The chat UI speaks the visitor's language */
  it("renders the header and composer from the translations", () => {
    render(
      <>
        <ChatHeader onNewChat={vi.fn()} onToggleConversations={vi.fn()} />
        <ChatComposer value="" onChange={vi.fn()} onSend={vi.fn()} />
      </>,
    );
    expect(screen.getByText(en.chat.subtitle)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: en.chat.input.newChat }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: en.chat.openConversations }),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(en.chat.input.placeholder),
    ).toBeInTheDocument();
  });

  /** Scenario: The chat UI speaks the visitor's language */
  it("has a Portuguese string for every English chat string", () => {
    const byName = (a: string, b: string): number => a.localeCompare(b);
    expect(keyPaths(pt.chat).sort(byName)).toEqual(
      keyPaths(en.chat).sort(byName),
    );
    expect(pt.chat.typing).not.toBe(en.chat.typing);
    expect(pt.chat.input.label).not.toBe(en.chat.input.label);
  });
});
