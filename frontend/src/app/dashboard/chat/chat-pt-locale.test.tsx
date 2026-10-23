/**
 * Gherkin: tests/features/chat-a11y-i18n.feature, tests/features/chat-polish.feature
 */
import { render as renderBare, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import pt from "@/i18n/locales/pt.json";
import { ChatComposer } from "./chat-composer";
import { ChatHeader } from "./chat-header";
import { ChatMessageList } from "./chat-message-list";

vi.mock("next-intl", async (importOriginal) => importOriginal());

function render(ui: React.ReactElement): ReturnType<typeof renderBare> {
  return renderBare(ui, {
    wrapper: ({ children }) => (
      <NextIntlClientProvider
        locale="pt"
        messages={pt}
        timeZone="America/Sao_Paulo"
      >
        {children}
      </NextIntlClientProvider>
    ),
  });
}

describe("chat in Portuguese", () => {
  /** Scenario: The chat UI speaks the visitor's language */
  it("renders the header, message box and typing label in Portuguese", () => {
    render(
      <>
        <ChatHeader onNewChat={vi.fn()} onToggleConversations={vi.fn()} />
        <ChatMessageList
          messages={[{ role: "user", text: "oi", time: "10:00" }]}
          isStreaming
        />
        <ChatComposer value="" onChange={vi.fn()} onSend={vi.fn()} />
      </>,
    );
    expect(screen.getByText(pt.chat.title)).toBeInTheDocument();
    expect(screen.getByText(pt.chat.subtitle)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: pt.chat.input.newChat }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: pt.chat.openConversations }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("log", { name: pt.chat.logLabel }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: pt.chat.input.label }),
    ).toHaveAttribute("placeholder", pt.chat.input.placeholder);
    expect(
      screen.getByRole("button", { name: pt.chat.input.send }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(pt.chat.typing).length).toBeGreaterThan(0);
  });

  /** Scenario: An empty chat introduces the Alter-Ego and suggests questions */
  it("introduces the Alter-Ego and suggests questions in Portuguese", () => {
    render(<ChatMessageList messages={[]} onSuggestion={vi.fn()} />);
    expect(
      screen.getByRole("heading", { name: pt.chat.empty.title }),
    ).toBeInTheDocument();
    for (const key of ["s1", "s2", "s3", "s4"] as const) {
      expect(
        screen.getByRole("button", { name: pt.chat.empty[key] }),
      ).toBeInTheDocument();
    }
  });
});
