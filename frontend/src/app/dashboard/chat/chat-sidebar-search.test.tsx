/**
 * Gherkin: tests/features/dashboard-chat.feature
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { ChatSidebar, filterConversations } from "./chat-sidebar";

const conversations = [
  { id: "1", name: "Pauta de outubro", time: "3h ago" },
  { id: "2", name: "Microsserviços ou monólito?", time: "1d ago" },
];

describe("chat sidebar", () => {
  /** Scenario: Searching conversations filters the list */
  it("matches titles ignoring case and accents", () => {
    expect(filterConversations(conversations, "MICROSSERVICOS")).toEqual([
      conversations[1],
    ]);
  });

  /** Scenario: An empty search shows every conversation */
  it("lists every conversation for an empty or blank query", () => {
    expect(filterConversations(conversations, "")).toEqual(conversations);
    expect(filterConversations(conversations, "  ")).toEqual(conversations);
  });

  /** Scenario: Searching conversations filters the list */
  it("filters as the user types and says when nothing matches", () => {
    render(
      <ChatSidebar
        conversations={conversations}
        activeConv="1"
        onSelectConversation={vi.fn()}
      />,
    );
    const search = screen.getByRole("searchbox", {
      name: "Search conversations",
    });

    fireEvent.change(search, { target: { value: "pauta" } });
    expect(screen.getByText("Pauta de outubro")).toBeInTheDocument();
    expect(screen.queryByText(/Microsserviços/)).not.toBeInTheDocument();

    fireEvent.change(search, { target: { value: "zzzz-no-match" } });
    expect(
      screen.getByText("No conversations match your search"),
    ).toBeInTheDocument();
  });

  /** Scenario: Conversations show their real titles and no invented avatars */
  it("shows titles and times without invented avatars", () => {
    render(
      <ChatSidebar
        conversations={conversations}
        activeConv="1"
        onSelectConversation={vi.fn()}
      />,
    );
    expect(screen.getByText("3h ago")).toBeInTheDocument();
    for (const fake of ["AE", "KB", "WF"]) {
      expect(screen.queryByText(fake)).not.toBeInTheDocument();
    }
  });
});
