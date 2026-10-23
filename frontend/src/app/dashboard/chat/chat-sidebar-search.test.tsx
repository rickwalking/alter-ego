/**
 * Gherkin: tests/features/dashboard-chat.feature
 */
import { describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import { ChatSidebar, filterConversations } from "./chat-sidebar";

const conversations = [
  { id: "1", name: "Pauta de outubro", time: "3h ago" },
  { id: "2", name: "Microsserviços ou monólito?", time: "1d ago" },
];

/** The sidebar with its search box wired the way the dashboard wires it. */
function SearchableSidebar(): React.ReactElement {
  const [query, setQuery] = useState("");
  return (
    <ChatSidebar
      conversations={filterConversations(conversations, query)}
      activeConv="1"
      onSelectConversation={vi.fn()}
      query={query}
      onQueryChange={setQuery}
    />
  );
}

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
    render(<SearchableSidebar />);
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

  /** Scenario: Searching conversations finds older ones too */
  it("waits for the server before saying nothing matches", () => {
    render(
      <ChatSidebar
        conversations={[]}
        activeConv=""
        onSelectConversation={vi.fn()}
        query="older chat"
        searching
      />,
    );
    expect(
      screen.queryByText("No conversations match your search"),
    ).not.toBeInTheDocument();
  });

  /** Scenario: Older conversations load a page at a time */
  it("offers more conversations only when there are more", () => {
    const onLoadMore = vi.fn();
    const { rerender } = render(
      <ChatSidebar
        conversations={conversations}
        activeConv="1"
        onSelectConversation={vi.fn()}
        hasMore
        onLoadMore={onLoadMore}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Show more" }));
    expect(onLoadMore).toHaveBeenCalledOnce();

    rerender(
      <ChatSidebar
        conversations={conversations}
        activeConv="1"
        onSelectConversation={vi.fn()}
        onLoadMore={onLoadMore}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Show more" }),
    ).not.toBeInTheDocument();
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
