/**
 * Gherkin: tests/features/dashboard-chat.feature
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
  apiCallNoContent: vi.fn(),
}));

import { apiCall } from "@/lib/api-client";
import { useSidebarConversations } from "./use-sidebar-conversations";

const mockApiCall = vi.mocked(apiCall);
const UPDATED = "2026-10-20T00:00:00Z";

function conversation(id: string, title: string) {
  return { id, title, metadata: {}, created_at: UPDATED, updated_at: UPDATED };
}

const firstPage = Array.from({ length: 20 }, (_, i) =>
  conversation(`c${i}`, `Chat ${i}`),
);
const olderPage = [conversation("old", "Microsserviços em 2024")];

function respond(url: string) {
  const params = new URL(url, "https://app.test").searchParams;
  if (params.get("search")) {
    return { items: olderPage, total: 1, limit: 100, offset: 0 };
  }
  const offset = Number(params.get("offset"));
  const items = offset === 0 ? firstPage : olderPage;
  return { items, total: 21, limit: 20, offset };
}

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return createElement(QueryClientProvider, { client }, children);
}

const requested = (): string[] => mockApiCall.mock.calls.map(([url]) => url);

beforeEach(() => {
  mockApiCall.mockReset();
  mockApiCall.mockImplementation((url) => Promise.resolve(respond(url)));
});

describe("useSidebarConversations", () => {
  /** Scenario: Older conversations load a page at a time */
  it("loads 20 conversations, then the next page on request", async () => {
    const { result } = renderHook(
      () => useSidebarConversations("en", "New conversation"),
      { wrapper },
    );
    await waitFor(() => expect(result.current.loaded).toHaveLength(20));
    expect(result.current.sidebar.hasMore).toBe(true);
    expect(requested()[0]).toContain("limit=20&offset=0");

    act(() => result.current.sidebar.onLoadMore());

    await waitFor(() => expect(result.current.loaded).toHaveLength(21));
    expect(requested()).toContainEqual(expect.stringContaining("offset=20"));
    expect(result.current.sidebar.hasMore).toBe(false);
  });

  /** Scenario: Searching conversations finds older ones too */
  it("asks the server for older matches once typing pauses", async () => {
    const { result } = renderHook(
      () => useSidebarConversations("en", "New conversation"),
      { wrapper },
    );
    await waitFor(() => expect(result.current.loaded).toHaveLength(20));

    act(() => result.current.sidebar.onQueryChange("microsservicos"));
    expect(result.current.sidebar.searching).toBe(true);
    expect(result.current.sidebar.hasMore).toBe(false);

    await waitFor(() =>
      expect(result.current.sidebar.conversations.map((c) => c.id)).toEqual([
        "old",
      ]),
    );
    expect(result.current.sidebar.searching).toBe(false);
    const searchUrl = requested().find((url) => url.includes("search="));
    expect(searchUrl).toContain("search=microsservicos");
    expect(searchUrl).toContain("limit=100");
  });

  /** Scenario: Searching conversations finds older ones too */
  it("lists loaded matches first and never repeats one", async () => {
    mockApiCall.mockImplementation((url) => {
      const response = respond(url);
      return Promise.resolve(
        url.includes("search=")
          ? { ...response, items: [firstPage[3]!, ...olderPage] }
          : response,
      );
    });
    const { result } = renderHook(
      () => useSidebarConversations("en", "New conversation"),
      { wrapper },
    );
    await waitFor(() => expect(result.current.loaded).toHaveLength(20));

    act(() => result.current.sidebar.onQueryChange("Chat 3"));

    await waitFor(() =>
      expect(result.current.sidebar.conversations.map((c) => c.id)).toEqual([
        "c3",
        "old",
      ]),
    );
  });
});
